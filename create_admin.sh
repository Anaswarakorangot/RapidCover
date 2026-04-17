#!/bin/bash
# Script to create the first admin user via the API

API_URL="${VITE_API_URL:-http://localhost:8000/api/v1}"

echo "Creating admin user via API..."
echo ""

response=$(curl -s -X POST "${API_URL}/admin/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rapidcover.in",
    "password": "admin123",
    "full_name": "Admin User"
  }')

# Check if response contains access_token (success)
if echo "$response" | grep -q "access_token"; then
  echo "[SUCCESS] Admin user created successfully!"
  echo ""
  echo "Login credentials:"
  echo "  Email:    admin@rapidcover.in"
  echo "  Password: admin123"
  echo ""
  echo "You can now login at: http://localhost:5173/login"
  echo "After login, you'll be redirected to: http://localhost:5173/admin"
else
  echo "[INFO] Response from server:"
  echo "$response"
  echo ""
  echo "If the error says 'Email already registered', the admin user already exists."
  echo "Use the credentials above to login."
fi
