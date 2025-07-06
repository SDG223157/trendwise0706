# Coolify Deployment Scripts for TrendWise

## Overview

I've created specialized bash scripts optimized for your **Python 3.9.23 Coolify environment** to handle the database connection issues and deploy the search optimization system.

## 📁 Files Created

### 1. `scripts/coolify_deploy_search_optimization.sh`
**Full deployment script** that:
- ✅ Forces SQLite database configuration
- ✅ Removes MySQL environment variables that cause conflicts
- ✅ Sets up database tables and migrations
- ✅ Configures search optimization system
- ✅ Creates health check and startup scripts
- ✅ Provides comprehensive logging and status checks

### 2. `scripts/coolify_quick_setup.sh`
**Quick setup script** for immediate use:
- ✅ Fast environment configuration
- ✅ Database table creation
- ✅ Basic system test
- ✅ Minimal output for quick debugging

### 3. `coolify.config.sh`
**Configuration reference** with:
- ✅ All environment variables needed
- ✅ Recommended Coolify settings
- ✅ Maintenance commands
- ✅ Troubleshooting commands

### 4. `coolify_health_check.py`
**Health monitoring script** that:
- ✅ Tests database connectivity
- ✅ Verifies search functionality
- ✅ Provides detailed system status
- ✅ Returns proper exit codes for monitoring

### 5. `coolify_startup.sh`
**Production startup script** that:
- ✅ Sets correct environment
- ✅ Runs health check
- ✅ Starts the Flask application

## 🚀 Coolify Deployment Options

### Option 1: Full Deployment (Recommended)
```bash
# Coolify Start Command:
bash scripts/coolify_deploy_search_optimization.sh && python wsgi.py
```

### Option 2: Quick Setup
```bash
# Coolify Start Command:
bash scripts/coolify_quick_setup.sh && python wsgi.py
```

### Option 3: Use Generated Startup Script
```bash
# After running the deployment script once:
bash coolify_startup.sh
```

## 🔧 Coolify Configuration

### Environment Variables
Set these in your Coolify environment:
```bash
MYSQL_DATABASE=default
MYSQL_HOST=n4ooskcwowss8ooss408k0gc
MYSQL_PASSWORD=j4zr2Z1ep1AJCEZonQWUvWezTis8wI8tUvfCDbIT9gv7NKghVZ67EjFOqA8I3bNz
MYSQL_PORT=3306
MYSQL_USER=mysql
FLASK_ENV=production
FLASK_APP=wsgi.py
```

**Note**: The MySQL host `n4ooskcwowss8ooss408k0gc` is only accessible within your Coolify network. DNS resolution errors during local testing are expected and normal.

### Build Command (optional)
```bash
pip install -r requirements.txt
```

### Health Check
- **Path**: `/health` (if your Flask app has this endpoint)
- **Command**: `python coolify_health_check.py`

## 🧪 Testing Your Setup

### 1. Quick Test
```bash
# In your Coolify terminal:
bash scripts/coolify_quick_setup.sh
```

### 2. Full System Test
```bash
# In your Coolify terminal:
bash scripts/coolify_deploy_search_optimization.sh
```

### 3. Health Check
```bash
# In your Coolify terminal:
python coolify_health_check.py
```

## 🔍 Troubleshooting

### MySQL Connection Errors
If you see MySQL authentication errors:
```bash
# Run this to force SQLite:
bash scripts/coolify_quick_setup.sh
```

### Database File Missing
```bash
# Check if database file exists:
ls -la trendwise.db

# If missing, run:
bash scripts/coolify_quick_setup.sh
```

### Python Environment Issues
```bash
# Check Python setup:
python -c "import sys; print(sys.version); import flask, sqlalchemy; print('OK')"
```

### Search Optimization Issues
```bash
# Check search system status:
python scripts/setup_search_optimization.py --status --coolify-mode
```

## 🛠️ Maintenance Commands

### System Status
```bash
python scripts/setup_search_optimization.py --status --coolify-mode
```

### Health Check
```bash
python coolify_health_check.py
```

### Populate Search Index
```bash
python scripts/populate_search_index.py populate
```

### Sync Search Index
```bash
python scripts/populate_search_index.py sync
```

## 📊 What These Scripts Fix

1. **Database Connection Issues**: Forces SQLite, removes MySQL variables
2. **Environment Configuration**: Sets proper paths and variables for Coolify
3. **Search Optimization**: Properly configures the search index system
4. **Health Monitoring**: Provides proper health checks for Coolify
5. **Startup Process**: Ensures proper application startup sequence

## 🎯 Next Steps

1. **Deploy to Coolify**: Use one of the start commands above
2. **Monitor Health**: Use the health check commands
3. **Populate Data**: When you have news articles, run the populate command
4. **Monitor Performance**: Check search optimization benefits

## 📋 Script Features

- ✅ **Python 3.9.23 Compatible**: Optimized for your exact environment
- ✅ **SQLite Forced**: Eliminates MySQL connection issues
- ✅ **Comprehensive Logging**: Detailed output for debugging
- ✅ **Error Handling**: Proper exit codes and error messages
- ✅ **Production Ready**: Suitable for live Coolify deployments
- ✅ **Modular Design**: Can run components independently

## 💡 Pro Tips

1. **Start Simple**: Try `coolify_quick_setup.sh` first
2. **Check Logs**: All scripts provide detailed logging
3. **Use Status Commands**: Regular status checks help monitor system health
4. **Gradual Deployment**: Test locally before full Coolify deployment

Your TrendWise application should now deploy smoothly in Coolify with the optimized search system! 