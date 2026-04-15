# 🎭 Demo Override Mode Guide

## Overview

Demo Override Mode allows you to demonstrate RapidCover features by **bypassing safety restrictions** on the **REAL database** with **REAL users**. This is NOT a simulation - it works with actual production data but disables certain safeguards to showcase features.

## What Demo Mode Does

Demo mode is an **override/bypass system** that:
- ✅ Works on REAL database with REAL partners
- ✅ Bypasses restrictions to demonstrate features
- ✅ Allows manual trigger creation for testing
- ✅ Uses mock data for external API calls (weather, AQI)
- ❌ Does NOT create fake data
- ❌ Does NOT simulate users

## Features Demonstrated

When Demo Mode is **ON**, you can:

### 1. **Bypass Adverse Selection Blocking** 🚫→✅
- **Normal Mode**: Cannot buy policy during active high-severity events
- **Demo Mode**: Can buy policy anytime, even during active events
- **Use Case**: Demonstrate that the adverse selection check exists without being blocked

### 2. **Bypass 7-Day Activity Gate** ⏰→✅
- **Normal Mode**: Must have 7+ active days before buying Standard/Pro tier
- **Demo Mode**: Can buy any tier immediately after registration
- **Use Case**: Register new user and immediately purchase Pro tier policy

### 3. **Manual Trigger Creation** 🎯
- Create REAL trigger events in the database
- Auto-generates REAL claims for partners with active policies
- Choose trigger type, zone, and severity
- **Use Case**: Showcase how automated claims work

### 4. **Mock External APIs** 🌐
- Uses mock data instead of calling OpenWeatherMap, WAQI APIs
- Prevents API quota usage during demos
- Allows demonstrations without API keys

## How to Use

### Step 1: Access Admin Panel
```
http://localhost:5173/admin
```

### Step 2: Go to Demo Mode Tab
Click on **"🎭 Demo Override"** in the admin navigation

### Step 3: Enable Demo Mode
Click the **"Enable Demo Mode"** button

You'll see:
- Orange banner at top: "🎭 DEMO MODE ACTIVE"
- List of active bypasses
- Manual trigger creation form

### Step 4: Demonstrate Features

**Test Adverse Selection Bypass:**
1. Create a high-severity trigger (severity 4+) in a zone
2. Try to register a new partner in that zone
3. Purchase a policy - it will succeed (normally blocked)

**Test Activity Gate Bypass:**
1. Register a brand new partner (no activity history)
2. Try to buy a Pro tier policy - it will succeed (normally requires 7+ days)

**Create Manual Triggers:**
1. Select a zone from the dropdown
2. Choose trigger type (rain, heat, AQI, shutdown, closure)
3. Set severity (1-5, where 3+ blocks enrollment)
4. Click "Create Trigger Event"
5. See claims auto-generated for partners in that zone

### Step 5: Exit Demo Mode
Click **"Disable Demo Mode"** to return to production safeguards

## Visual Indicators

When Demo Mode is active:
- ⚠️ **Orange banner** at top: "🎭 DEMO MODE ACTIVE"
- Admin panel shows bypass status
- All actions work on REAL database

## API Endpoints

Demo mode provides these endpoints:

```bash
# Check status
GET /api/v1/admin/panel/demo-mode/status

# Toggle on/off
POST /api/v1/admin/panel/demo-mode/toggle?enabled=true

# Create manual trigger
POST /api/v1/admin/panel/demo-mode/create-trigger?zone_id=1&trigger_type=rain&severity=4
```

## Use Cases

### 1. **Investor Presentations**
- Show adverse selection protection exists (create high-severity event)
- Bypass it to complete purchase flow demonstration
- Demonstrate automated claim generation via manual triggers

### 2. **Stakeholder Demos**
- Register new partner, immediately buy Pro tier (bypassing activity gate)
- Create trigger events to show automated payout flow
- Prove features work end-to-end

### 3. **Feature Verification**
- Test that restrictions are working (enable → disable demo mode)
- Verify triggers generate claims correctly
- Confirm adverse selection blocks as expected

### 4. **Training Sessions**
- Teach ops team about trigger types
- Demonstrate claim auto-generation
- Show fraud prevention checks

## Example Workflow

```bash
# 1. Enable demo mode
POST /admin/panel/demo-mode/toggle?enabled=true

# 2. Register new partner at 9063990119
POST /api/v1/partners/register
{
  "name": "Test Partner",
  "phone": "9999999999",
  "email": "test@example.com",
  ...
}

# 3. Buy Pro tier immediately (bypasses 7-day gate)
POST /api/v1/policies
{
  "tier": "pro",
  ...
}

# 4. Create rain trigger in their zone
POST /admin/panel/demo-mode/create-trigger?zone_id=1&trigger_type=rain&severity=4

# 5. See claim auto-generated and approved

# 6. Disable demo mode
POST /admin/panel/demo-mode/toggle?enabled=false
```

## Important Notes

⚠️ **Production Safety**
- Demo mode works on REAL database - all changes are permanent
- Claims created are REAL claims (will show in reports)
- Disable demo mode after demonstrations
- Do NOT leave demo mode enabled in production

✅ **Best Practices**
- Always toggle OFF after demonstrations
- Inform audience that restrictions are bypassed for demo only
- Use for presentations, not for production testing
- Monitor database for demo-created data

🎯 **Showcase Tips**
- Start with bypass explanations (what's normally blocked)
- Create trigger to show automated claims
- Register new user and buy policy immediately
- Exit demo mode to prove restrictions still work

## Differences from Production

| Feature | Production Mode | Demo Mode |
|---------|----------------|-----------|
| Adverse Selection | ✅ Blocks enrollment during events | ❌ Bypassed |
| Activity Gate | ✅ Requires 7+ days for Pro/Standard | ❌ Bypassed |
| External APIs | ✅ Calls live APIs | ❌ Uses mock data |
| Database | ✅ Real database | ✅ Real database |
| Users | ✅ Real partners | ✅ Real partners |
| Claims | ✅ Real claims | ✅ Real claims |

## Quick Start

```bash
# 1. Start backend (must be running)
cd backend
uvicorn app.main:app --reload

# 2. Start frontend
cd frontend
npm run dev

# 3. Open admin panel
http://localhost:5173/admin

# 4. Click "🎭 Demo Override" tab

# 5. Toggle demo mode ON

# 6. Create triggers and demonstrate features!
```

## Troubleshooting

**Demo mode not toggling?**
- Check backend is running on port 8000
- Verify `/admin/panel/demo-mode/toggle` endpoint is accessible
- Check browser console for errors

**Bypasses not working?**
- Refresh status: GET `/admin/panel/demo-mode/status`
- Verify `demo_mode: true` in response
- Check backend logs for demo mode state

**Trigger creation failing?**
- Ensure zone_id exists in database
- Check for existing active trigger of same type in that zone
- Verify severity is between 1-5

**Want to verify bypasses work?**
- Create severity 4+ trigger in a zone
- Try to buy policy in that zone
- In production mode: blocked ❌
- In demo mode: succeeds ✅

---

**Questions?** Check the demo mode panel for real-time status and bypass information!
