#!/usr/bin/env python3
"""
Dubai Events Data Collection - Main Entry Point
Perplexity AI-based event discovery and extraction system

This replaces the old Firecrawl-based system with a simpler, more efficient approach.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional
from loguru import logger
import argparse

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from run_perplexity_collection import PerplexityDataCollectionPipeline
from monitoring.logging_config import PerplexityMonitoringSystem, quick_health_check
from config.perplexity_settings import get_settings

def setup_logging():
    """Setup enhanced logging for the main entry point"""
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # File handler
    log_file = Path("logs/main.log")
    log_file.parent.mkdir(exist_ok=True)
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days"
    )

async def run_health_check():
    """Run comprehensive health check"""
    logger.info("🏥 Starting system health check...")
    
    monitor = PerplexityMonitoringSystem()
    results = monitor.run_all_health_checks()
    
    print(f"\n{'='*60}")
    print(f"🏥 SYSTEM HEALTH REPORT")
    print(f"{'='*60}")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Services: {results['summary']['healthy_services']}/{results['summary']['total_services']} healthy")
    
    if results['summary']['avg_response_time_ms']:
        print(f"Average Response Time: {results['summary']['avg_response_time_ms']}ms")
    
    print(f"\nService Details:")
    for service, details in results['services'].items():
        status_emoji = "✅" if details['status'] == 'healthy' else "❌"
        print(f"  {status_emoji} {service.replace('_', ' ').title()}: {details['status']}")
        
        if details.get('error'):
            print(f"    Error: {details['error']}")
        if details.get('response_time_ms'):
            print(f"    Response Time: {details['response_time_ms']}ms")
    
    print(f"{'='*60}\n")
    
    return results['overall_status'] == 'healthy'

async def run_data_collection(mode: str = "comprehensive", categories: Optional[List[str]] = None):
    """Run data collection with specified mode and categories"""
    
    # Health check first
    if not await run_health_check():
        logger.error("❌ Health check failed. Please fix issues before running data collection.")
        return False
    
    logger.info(f"🚀 Starting {mode} data collection...")
    
    pipeline = PerplexityDataCollectionPipeline()
    
    try:
        if mode == "test":
            results = await pipeline.run_test_extraction()
        elif mode == "targeted" and categories:
            results = await pipeline.run_targeted_extraction(categories)
        elif mode == "comprehensive":
            results = await pipeline.run_comprehensive_extraction()
        elif mode == "quick":
            # Quick mode: just a few targeted searches
            results = await pipeline.run_targeted_extraction(["family", "entertainment"])
        else:
            logger.error(f"❌ Unknown mode: {mode}")
            return False
        
        # Summary
        logger.success(f"✅ Data collection completed successfully!")
        logger.info(f"📊 Results: {results}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Data collection failed: {e}")
        return False

async def run_status_check():
    """Run status check and show database statistics"""
    logger.info("📊 Checking current database status...")
    
    pipeline = PerplexityDataCollectionPipeline()
    stats = await pipeline.get_collection_stats()
    
    print(f"\n{'='*60}")
    print(f"📊 DATABASE STATUS")
    print(f"{'='*60}")
    print(f"Total Events: {stats.get('total_events', 0)}")
    print(f"Family Events: {stats.get('family_events', 0)}")
    print(f"Adult Events: {stats.get('adult_events', 0)}")
    print(f"Last Updated: {stats.get('last_updated', 'Never')}")
    print(f"{'='*60}\n")

def main():
    """Main entry point with command line interface"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="Dubai Events Data Collection - Perplexity AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py health                     # Run health check only
  python main.py status                     # Show database status
  python main.py collect --mode test        # Test collection (few events)
  python main.py collect --mode quick       # Quick collection (family + entertainment)
  python main.py collect --mode comprehensive # Full collection (all categories)
  python main.py collect --mode targeted --categories family cultural entertainment
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Run system health check')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show database status')
    
    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Run data collection')
    collect_parser.add_argument(
        '--mode', 
        choices=['test', 'quick', 'targeted', 'comprehensive'],
        default='comprehensive',
        help='Collection mode (default: comprehensive)'
    )
    collect_parser.add_argument(
        '--categories',
        nargs='+',
        help='Specific categories for targeted mode'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    logger.info("🌟 Dubai Events Data Collection - Perplexity AI System")
    logger.info("📍 Simplified, efficient event discovery for Dubai")
    
    try:
        if args.command == 'health':
            success = asyncio.run(run_health_check())
            sys.exit(0 if success else 1)
            
        elif args.command == 'status':
            asyncio.run(run_status_check())
            
        elif args.command == 'collect':
            success = asyncio.run(run_data_collection(
                mode=args.mode,
                categories=args.categories
            ))
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        logger.info("⚠️ Collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 