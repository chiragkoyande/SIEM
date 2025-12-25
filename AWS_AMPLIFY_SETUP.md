# AWS Amplify Deployment Guide for SentinelWatch SIEM

## PostgreSQL Database Setup

### Option 1: AWS RDS PostgreSQL (Recommended)

1. **Create RDS Instance**
   - Go to AWS Console → RDS → Create database
   - Choose PostgreSQL (latest version)
   - Free tier: `db.t3.micro` (up to 750 hours/month)
   - Set username/password
   - Enable public access for Amplify

2. **Get Database URL**
   ```
   DATABASE_URL=postgresql://username:password@host:5432/database_name
   ```

3. **Security Group Settings**
   - Add inbound rule for Amplify IP ranges
   - Allow port 5432 from 0.0.0.0/0 (for testing)
   - Restrict to specific IPs in production

### Option 2: AWS Aurora Serverless PostgreSQL

1. **Create Aurora Cluster**
   - AWS Console → RDS → Create cluster
   - Choose Amazon Aurora PostgreSQL
   - Serverless v2 configuration
   - Pay-per-use pricing

2. **Connection String**
   ```
   DATABASE_URL=postgresql://username:password@cluster-endpoint:5432/database_name
   ```

### Option 3: External PostgreSQL Services

#### Supabase (Free Tier)
1. Sign up at https://supabase.com
2. Create new project
3. Get connection string from Settings → Database
4. Format: `postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres`

#### Railway (Free Tier)
1. Sign up at https://railway.app
2. Add PostgreSQL service
3. Get connection URL from service settings

#### Neon (Free Tier)
1. Sign up at https://neon.tech
2. Create new project
3. Get connection string from dashboard

## AWS Amplify Setup Steps

### 1. Prepare Your Code

```bash
# Install dependencies
pip install -r requirements.txt

# Test locally with PostgreSQL
export DATABASE_URL="postgresql://user:pass@host:5432/db"
python main.py
```

### 2. Update Environment Variables

In `.env.example`:
```env
DATABASE_URL=postgresql://username:password@host:5432/database_name
CORS_ORIGINS=https://your-app.amplifyapp.com
SECRET_KEY=your-secure-secret-key-here
```

### 3. Create Amplify App

1. **Connect to GitHub**
   - AWS Console → Amplify → Create app
   - Connect to your GitHub repository
   - Select branch (main/master)

2. **Build Settings**
   ```yaml
   version: 1
   backend:
     phases:
       preBuild:
         commands:
           - python -m pip install --upgrade pip
           - pip install -r requirements.txt
       build:
         commands:
           - python -c "from backend.app.models.database import init_db; init_db()"
   artifacts:
     baseDirectory: /
     files:
       - '**/*'
   cache:
     paths:
       - '$HOME/.cache/pip/**/*'
   ```

3. **Environment Variables**
   - Go to App settings → Environment variables
   - Add `DATABASE_URL` (your PostgreSQL connection string)
   - Add `SECRET_KEY` (generate secure key)
   - Add `CORS_ORIGINS` (your Amplify domain)

### 4. Deploy

1. **Initial Build**
   - Amplify will automatically build and deploy
   - Monitor build logs for any errors

2. **Database Migration**
   - SQLAlchemy will auto-create tables on first run
   - Verify tables created in PostgreSQL

### 5. Test Deployment

```bash
# Health check
curl https://your-app.amplifyapp.com/health

# API test
curl https://your-app.amplifyapp.com/api/dashboard/stats
```

## Database URL Examples

### AWS RDS
```
postgresql://admin:MyPassword123@my-instance.rds.amazonaws.com:5432/sentinelwatch
```

### Supabase
```
postgresql://postgres:abc123xyz@db.abc123xyz.supabase.co:5432/postgres
```

### Railway
```
postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway
```

### Neon
```
postgresql://user:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/dbname?sslmode=require
```

## Security Recommendations

1. **Environment Variables**
   - Never commit database credentials to Git
   - Use Amplify environment variables
   - Rotate passwords regularly

2. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Restrict IP access in production

3. **CORS Settings**
   - Set specific allowed origins
   - Disable wildcard `*` in production

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL format
   - Verify security group settings
   - Ensure database is running

2. **Build Failures**
   - Check Python version compatibility
   - Verify all dependencies in requirements.txt
   - Review build logs

3. **CORS Errors**
   - Update CORS_ORIGINS environment variable
   - Include your Amplify domain

### Debug Commands

```bash
# Test database connection
python -c "
from sqlalchemy import create_engine
engine = create_engine('$DATABASE_URL')
print('Database connection successful')
"

# Check tables
python -c "
from backend.app.models.database import engine, Base
Base.metadata.create_all(engine)
print('Tables created successfully')
"
```

## Cost Optimization

- Use free tier databases (Supabase, Neon, Railway)
- Monitor RDS instance usage
- Set up billing alerts
- Consider serverless options for variable workloads

## Next Steps

1. Set up PostgreSQL database
2. Update environment variables
3. Deploy to Amplify
4. Test all API endpoints
5. Set up monitoring and alerts
