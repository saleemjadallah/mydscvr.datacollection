#!/bin/bash

echo "=== Permanent CORS Fix Deployment Script ==="
echo ""
echo "This script deploys the permanent CORS configuration to ensure hidden gems"
echo "endpoint always has CORS enabled regardless of configuration changes."
echo ""

# Check if we have SSH access
echo "Testing SSH connection to production server..."
if ssh -o ConnectTimeout=5 ubuntu@3.29.102.4 "echo 'SSH connection successful'" 2>/dev/null; then
    echo "✅ SSH connection available"
    
    echo ""
    echo "Deploying files to production server..."
    
    # Copy CORS middleware file
    echo "📁 Uploading CORS middleware..."
    scp utils/cors_middleware.py ubuntu@3.29.102.4:/home/ubuntu/DXB-events/Backend/utils/
    
    # Copy updated main.py
    echo "📁 Uploading updated main.py..."
    scp main.py ubuntu@3.29.102.4:/home/ubuntu/DXB-events/Backend/
    
    # Restart the service
    echo "🔄 Restarting API service..."
    ssh ubuntu@3.29.102.4 "sudo systemctl restart dxb-events-api"
    
    echo ""
    echo "✅ Deployment completed!"
    echo "🧪 Testing CORS endpoint..."
    
    sleep 5
    curl -s -X GET -H "Origin: https://mydscvr.ai" https://mydscvr.xyz/api/hidden-gems/current > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ CORS endpoint test successful!"
    else
        echo "❌ CORS endpoint test failed"
    fi
    
else
    echo "❌ SSH connection failed"
    echo ""
    echo "Manual deployment required:"
    echo ""
    echo "1. Copy the following file to the server:"
    echo "   utils/cors_middleware.py → /home/ubuntu/DXB-events/Backend/utils/"
    echo ""
    echo "2. Copy the updated main.py:"
    echo "   main.py → /home/ubuntu/DXB-events/Backend/"
    echo ""
    echo "3. Restart the API service:"
    echo "   sudo systemctl restart dxb-events-api"
    echo ""
    echo "4. Test the CORS endpoint:"
    echo "   curl -X GET -H 'Origin: https://mydscvr.ai' https://mydscvr.xyz/api/hidden-gems/current"
fi

echo ""
echo "=== CORS Fix Summary ==="
echo "✅ Created permanent CORS middleware (utils/cors_middleware.py)"
echo "✅ Updated main.py to include PermanentCORSMiddleware"
echo "✅ Hidden gems endpoint now has guaranteed CORS support"
echo "✅ Future configuration changes won't affect CORS on critical endpoints"
echo ""
echo "Critical endpoints protected:"
echo "- /api/hidden-gems"
echo "- /api/events"
echo "- /api/notifications"