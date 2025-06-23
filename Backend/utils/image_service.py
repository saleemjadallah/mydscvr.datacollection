"""
Image processing and optimization service for DXB Events API
Phase 4: Data Integration implementation
"""

import io
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import os
import base64

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from config import settings


class ImageService:
    """
    Comprehensive image processing service for event images
    """
    
    def __init__(self):
        self.max_file_size = 5 * 1024 * 1024  # 5MB max
        self.supported_formats = ['JPEG', 'PNG', 'WEBP', 'GIF']
        self.thumbnail_sizes = {
            'small': (150, 150),
            'medium': (400, 300),
            'large': (800, 600)
        }
        
        # CDN and storage configuration
        self.cdn_base_url = getattr(settings, 'cdn_base_url', 'https://cdn.dxb-events.com')
        self.storage_path = getattr(settings, 'image_storage_path', './storage/images')
        self.aws_s3_bucket = getattr(settings, 'aws_s3_bucket', None)
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
    
    async def process_event_images(self, event_id: str, image_urls: List[str]) -> Dict[str, Any]:
        """
        Process all images for an event
        """
        try:
            processed_images = []
            failed_images = []
            total_size = 0
            
            for i, image_url in enumerate(image_urls[:10]):  # Limit to 10 images per event
                try:
                    result = await self.process_single_image(
                        image_url, 
                        event_id, 
                        f"image_{i+1}"
                    )
                    
                    if result['success']:
                        processed_images.append(result)
                        total_size += result.get('file_size', 0)
                    else:
                        failed_images.append({
                            'url': image_url,
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    failed_images.append({
                        'url': image_url,
                        'error': str(e)
                    })
            
            return {
                'event_id': event_id,
                'processed_count': len(processed_images),
                'failed_count': len(failed_images),
                'total_size_bytes': total_size,
                'processed_images': processed_images,
                'failed_images': failed_images,
                'processing_time': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'event_id': event_id,
                'success': False,
                'error': f"Image processing failed: {str(e)}"
            }
    
    async def process_single_image(
        self, 
        image_url: str, 
        event_id: str, 
        image_name: str
    ) -> Dict[str, Any]:
        """
        Process a single image: download, validate, optimize, and store
        """
        try:
            # Validate URL
            if not self._is_valid_image_url(image_url):
                return {
                    'success': False,
                    'error': 'Invalid image URL format'
                }
            
            # Download image
            image_data = await self._download_image(image_url)
            if not image_data:
                return {
                    'success': False,
                    'error': 'Failed to download image'
                }
            
            # Validate image
            validation_result = self._validate_image(image_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f"Invalid image: {validation_result['error']}"
                }
            
            # Generate unique filename
            file_hash = hashlib.md5(image_data).hexdigest()[:12]
            base_filename = f"{event_id}_{image_name}_{file_hash}"
            
            # Process and optimize image
            if PIL_AVAILABLE:
                optimized_images = await self._optimize_image(image_data, base_filename)
            else:
                # Fallback: save original image without optimization
                optimized_images = await self._save_original_image(image_data, base_filename)
            
            # Store images (local or cloud)
            storage_result = await self._store_images(optimized_images)
            
            return {
                'success': True,
                'original_url': image_url,
                'file_hash': file_hash,
                'file_size': len(image_data),
                'format': validation_result.get('format', 'unknown'),
                'dimensions': validation_result.get('dimensions', {}),
                'optimized_urls': storage_result.get('urls', {}),
                'cdn_urls': storage_result.get('cdn_urls', {}),
                'storage_path': storage_result.get('storage_path', ''),
                'processing_metadata': {
                    'processed_at': datetime.now(timezone.utc).isoformat(),
                    'optimization_enabled': PIL_AVAILABLE,
                    'thumbnails_generated': len(optimized_images) > 1
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Image processing error: {str(e)}"
            }
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        Validate if URL looks like a valid image URL
        """
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
            
            # Check if URL ends with image extension
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            path_lower = parsed.path.lower()
            
            return any(path_lower.endswith(ext) for ext in image_extensions)
            
        except Exception:
            return False
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """
        Download image from URL with safety checks
        """
        try:
            headers = {
                'User-Agent': 'DXB-Events-ImageBot/1.0',
                'Accept': 'image/*'
            }
            
            response = requests.get(
                url, 
                headers=headers, 
                timeout=30,
                stream=True
            )
            
            if response.status_code != 200:
                return None
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                return None
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_file_size:
                return None
            
            # Download with size limit
            image_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                image_data += chunk
                if len(image_data) > self.max_file_size:
                    return None
            
            return image_data
            
        except Exception as e:
            print(f"Image download failed: {e}")
            return None
    
    def _validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Validate image data and extract metadata
        """
        try:
            if not PIL_AVAILABLE:
                # Basic validation without PIL
                if len(image_data) < 100:  # Too small to be a valid image
                    return {'valid': False, 'error': 'Image too small'}
                
                # Check for basic image headers
                headers = {
                    b'\xFF\xD8\xFF': 'JPEG',
                    b'\x89PNG\r\n\x1a\n': 'PNG',
                    b'GIF87a': 'GIF',
                    b'GIF89a': 'GIF',
                    b'RIFF': 'WEBP'  # Simplified WEBP check
                }
                
                for header, format_name in headers.items():
                    if image_data.startswith(header):
                        return {
                            'valid': True,
                            'format': format_name,
                            'dimensions': {'width': 0, 'height': 0}  # Unknown without PIL
                        }
                
                return {'valid': False, 'error': 'Unrecognized image format'}
            
            # Full validation with PIL
            try:
                with Image.open(io.BytesIO(image_data)) as img:
                    # Check format
                    if img.format not in self.supported_formats:
                        return {
                            'valid': False,
                            'error': f'Unsupported format: {img.format}'
                        }
                    
                    # Check dimensions
                    width, height = img.size
                    if width < 50 or height < 50:
                        return {
                            'valid': False,
                            'error': 'Image dimensions too small'
                        }
                    
                    if width > 4000 or height > 4000:
                        return {
                            'valid': False,
                            'error': 'Image dimensions too large'
                        }
                    
                    return {
                        'valid': True,
                        'format': img.format,
                        'dimensions': {
                            'width': width,
                            'height': height
                        },
                        'mode': img.mode,
                        'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                    }
                    
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Invalid image data: {str(e)}'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }
    
    async def _optimize_image(self, image_data: bytes, base_filename: str) -> Dict[str, bytes]:
        """
        Optimize image and create multiple sizes
        """
        try:
            optimized_images = {}
            
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Original optimized
                original_buffer = io.BytesIO()
                img.save(
                    original_buffer, 
                    format='JPEG', 
                    quality=85, 
                    optimize=True
                )
                optimized_images[f"{base_filename}_original.jpg"] = original_buffer.getvalue()
                
                # Generate thumbnails
                for size_name, (width, height) in self.thumbnail_sizes.items():
                    # Create thumbnail
                    thumb = img.copy()
                    thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
                    
                    # Save thumbnail
                    thumb_buffer = io.BytesIO()
                    thumb.save(
                        thumb_buffer,
                        format='JPEG',
                        quality=80,
                        optimize=True
                    )
                    
                    optimized_images[f"{base_filename}_{size_name}.jpg"] = thumb_buffer.getvalue()
            
            return optimized_images
            
        except Exception as e:
            print(f"Image optimization failed: {e}")
            # Fallback to original
            return await self._save_original_image(image_data, base_filename)
    
    async def _save_original_image(self, image_data: bytes, base_filename: str) -> Dict[str, bytes]:
        """
        Save original image without optimization (fallback)
        """
        try:
            # Determine extension from image data
            extension = '.jpg'  # Default
            if image_data.startswith(b'\x89PNG'):
                extension = '.png'
            elif image_data.startswith(b'GIF'):
                extension = '.gif'
            elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:20]:
                extension = '.webp'
            
            filename = f"{base_filename}_original{extension}"
            return {filename: image_data}
            
        except Exception as e:
            print(f"Failed to save original image: {e}")
            return {}
    
    async def _store_images(self, optimized_images: Dict[str, bytes]) -> Dict[str, Any]:
        """
        Store images to local storage or cloud (S3)
        """
        try:
            stored_urls = {}
            cdn_urls = {}
            storage_paths = []
            
            for filename, image_data in optimized_images.items():
                # Local storage
                file_path = os.path.join(self.storage_path, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                storage_paths.append(file_path)
                stored_urls[filename] = f"/images/{filename}"
                cdn_urls[filename] = f"{self.cdn_base_url}/images/{filename}"
                
                # TODO: Upload to S3 if configured
                if self.aws_s3_bucket:
                    s3_url = await self._upload_to_s3(filename, image_data)
                    if s3_url:
                        cdn_urls[filename] = s3_url
            
            return {
                'urls': stored_urls,
                'cdn_urls': cdn_urls,
                'storage_path': '; '.join(storage_paths),
                'storage_type': 'local' if not self.aws_s3_bucket else 's3'
            }
            
        except Exception as e:
            print(f"Image storage failed: {e}")
            return {
                'urls': {},
                'cdn_urls': {},
                'storage_path': '',
                'error': str(e)
            }
    
    async def _upload_to_s3(self, filename: str, image_data: bytes) -> Optional[str]:
        """
        Upload image to AWS S3 (placeholder for future implementation)
        """
        try:
            # TODO: Implement S3 upload using boto3
            # For now, return placeholder URL
            return f"https://s3.amazonaws.com/{self.aws_s3_bucket}/events/{filename}"
            
        except Exception as e:
            print(f"S3 upload failed: {e}")
            return None
    
    async def get_image_metadata(self, image_path: str) -> Dict[str, Any]:
        """
        Get metadata for a stored image
        """
        try:
            if not os.path.exists(image_path):
                return {'error': 'Image not found'}
            
            file_stats = os.stat(image_path)
            metadata = {
                'file_path': image_path,
                'file_size': file_stats.st_size,
                'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            }
            
            if PIL_AVAILABLE:
                try:
                    with Image.open(image_path) as img:
                        metadata.update({
                            'dimensions': {
                                'width': img.width,
                                'height': img.height
                            },
                            'format': img.format,
                            'mode': img.mode
                        })
                except Exception:
                    pass
            
            return metadata
            
        except Exception as e:
            return {'error': f"Failed to get image metadata: {str(e)}"}
    
    async def cleanup_old_images(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up old, unused images
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_timestamp = cutoff_date.timestamp()
            
            cleaned_files = []
            total_size_freed = 0
            errors = []
            
            for filename in os.listdir(self.storage_path):
                file_path = os.path.join(self.storage_path, filename)
                
                try:
                    file_stats = os.stat(file_path)
                    
                    # Check if file is old enough
                    if file_stats.st_mtime < cutoff_timestamp:
                        file_size = file_stats.st_size
                        os.remove(file_path)
                        
                        cleaned_files.append(filename)
                        total_size_freed += file_size
                        
                except Exception as e:
                    errors.append(f"Failed to clean {filename}: {str(e)}")
            
            return {
                'cleaned_files_count': len(cleaned_files),
                'total_size_freed_bytes': total_size_freed,
                'total_size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
                'errors': errors,
                'cleanup_date': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Cleanup failed: {str(e)}"
            }
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get storage usage statistics
        """
        try:
            total_files = 0
            total_size = 0
            file_types = {}
            
            for filename in os.listdir(self.storage_path):
                file_path = os.path.join(self.storage_path, filename)
                
                if os.path.isfile(file_path):
                    total_files += 1
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    # Count by file type
                    ext = os.path.splitext(filename)[1].lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types,
                'storage_path': self.storage_path,
                'pil_available': PIL_AVAILABLE,
                'last_checked': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'error': f"Failed to get storage statistics: {str(e)}"
            } 