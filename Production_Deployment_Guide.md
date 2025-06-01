# Speaking Meeting Bot - Production Deployment Guide

## 📋 Prerequisites

Before starting the deployment process, ensure you have:

- **GitHub Account** (for code hosting)
- **Netlify Account** (for frontend hosting) 
- **Render Account** (for backend hosting)
- **Domain Name** (optional, but recommended)
- **API Keys** for all required services

### Required API Keys:
- OpenAI API Key
- Cartesia API Key  
- Deepgram API Key
- MeetingBaas API Key
- Replicate API Key

---

## 🚀 Backend Deployment (Render)

### Step 1: Prepare the Repository

1. **Fork/Clone the repository** to your GitHub account
2. **Push to GitHub** if working locally:
   ```bash
   git add .
   git commit -m "Initial production deployment"
   git push origin main
   ```

### Step 2: Create Render Web Service

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Connect GitHub Repository**:
   - Select your forked repository
   - Choose the `main` branch

### Step 3: Configure Render Service

**Basic Settings:**
- **Name**: `speaking-meeting-bot-backend`
- **Region**: Choose closest to your users (US East recommended)
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Docker`

**Build & Deploy Settings:**
- **Build Command**: Leave blank (uses Dockerfile)
- **Start Command**: Leave blank (uses Dockerfile CMD)

### Step 4: Set Environment Variables

In Render dashboard, add these environment variables:

```bash
# API Keys (Required)
OPENAI_API_KEY=your_openai_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
MEETING_BAAS_API_KEY=your_meetingbaas_api_key_here
REPLICATE_API_TOKEN=your_replicate_api_key_here

# Server Configuration
PORT=8766
HOST=0.0.0.0
ENVIRONMENT=production

# CORS Configuration
FRONTEND_URL=https://your-netlify-app.netlify.app

# Database (if using external database)
DATABASE_URL=your_database_url_here

# Additional Configuration
LOG_LEVEL=INFO
MAX_WORKERS=4
```

### Step 5: Deploy Backend

1. **Click "Create Web Service"**
2. **Wait for deployment** (usually 5-10 minutes)
3. **Note the backend URL**: `https://your-service-name.onrender.com`

---

## 🌐 Frontend Deployment (Netlify)

### Step 1: Prepare Frontend Build

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Update API configuration** in `src/services/api.js`:
   - Ensure `VITE_API_URL` points to your Render backend URL

### Step 2: Create Netlify Site

1. **Go to Netlify Dashboard**: https://app.netlify.com
2. **Click "Add new site"** → **"Import an existing project"**
3. **Connect to Git provider** (GitHub)
4. **Select your repository**

### Step 3: Configure Build Settings

**Site Settings:**
- **Base directory**: `frontend`
- **Build command**: `npm run build`
- **Publish directory**: `frontend/dist`
- **Node version**: `18` (add in netlify.toml)

### Step 4: Set Environment Variables

In Netlify dashboard, go to **Site Settings** → **Environment Variables**:

```bash
# Backend API URL
VITE_API_URL=https://your-render-service.onrender.com

# API Keys (if needed by frontend)
VITE_MEETING_BAAS_API_KEY=your_meetingbaas_api_key_here

# Build Configuration
NODE_VERSION=18
```

### Step 5: Create netlify.toml Configuration

Create `frontend/netlify.toml`:

```toml
[build]
  base = "frontend"
  publish = "dist"
  command = "npm run build"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/api/*"
  to = "https://your-render-service.onrender.com/:splat"
  status = 200
  force = true

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[dev]
  command = "npm run dev"
  port = 5173
```

### Step 6: Deploy Frontend

1. **Click "Deploy site"**
2. **Wait for build completion** (2-5 minutes)
3. **Note the frontend URL**: `https://random-name.netlify.app`

---

## 🔧 Post-Deployment Configuration

### Update CORS Settings

1. **Update backend environment variable**:
   ```bash
   FRONTEND_URL=https://your-actual-netlify-url.netlify.app
   ```

2. **Redeploy backend** on Render

### Custom Domain Setup (Optional)

**For Netlify:**
1. Go to **Site Settings** → **Domain management**
2. **Add custom domain**
3. **Update DNS records** as instructed

**For Render:**
1. Go to **Settings** → **Custom Domains**
2. **Add custom domain**
3. **Update DNS records** as instructed

---

## ✅ Verification & Testing

### Backend Health Check

1. **Visit**: `https://your-render-service.onrender.com/`
2. **Expected response**: API status message
3. **Check**: `https://your-render-service.onrender.com/docs` for API documentation

### Frontend Functionality Test

1. **Visit your Netlify URL**
2. **Test features**:
   - ✅ Persona creation/management
   - ✅ Bot creation/management  
   - ✅ API connectivity
   - ✅ Real-time updates

### API Integration Test

1. **Create a test persona**
2. **Create a test bot**
3. **Verify backend logs** in Render dashboard

---

## 🔒 Security Best Practices

### Environment Variables Security

- ✅ **Never commit API keys** to Git
- ✅ **Use environment variables** for all secrets
- ✅ **Rotate API keys** regularly
- ✅ **Monitor API usage** for unusual activity

### Network Security

- ✅ **Enable HTTPS** (automatic on both platforms)
- ✅ **Configure proper CORS** settings
- ✅ **Use secure headers** in responses
- ✅ **Implement rate limiting** if needed

---

## 📊 Monitoring & Maintenance

### Render Monitoring

- **View logs**: Render Dashboard → Logs
- **Monitor resources**: Check CPU/Memory usage
- **Set up alerts**: For service downtime
- **Monitor costs**: Track usage-based billing

### Netlify Monitoring

- **Build logs**: Available in deploy section
- **Analytics**: Available with Pro plan
- **Form submissions**: If using Netlify forms
- **Function logs**: If using Netlify functions

### Regular Maintenance Tasks

1. **Weekly**:
   - ✅ Check service health
   - ✅ Review error logs
   - ✅ Monitor API costs

2. **Monthly**:
   - ✅ Update dependencies
   - ✅ Review security patches
   - ✅ Backup data/configurations
   - ✅ Cost optimization review

---

## 🚨 Troubleshooting Common Issues

### Backend Issues

**Service won't start:**
- ✅ Check Dockerfile syntax
- ✅ Verify all environment variables
- ✅ Check port configuration (8766)
- ✅ Review build logs

**API calls failing:**
- ✅ Verify CORS configuration
- ✅ Check API key validity
- ✅ Test endpoints individually
- ✅ Review network logs

### Frontend Issues

**Build failures:**
- ✅ Check Node.js version (18+)
- ✅ Verify package.json syntax
- ✅ Clear npm cache: `npm cache clean --force`
- ✅ Check for missing dependencies

**API connection issues:**
- ✅ Verify VITE_API_URL is correct
- ✅ Check CORS headers
- ✅ Test API endpoints directly
- ✅ Review browser console errors

---

## 💰 Cost Optimization Tips

### Render Optimizations

1. **Right-size your plan** based on actual usage
2. **Use sleep mode** for development environments
3. **Monitor resource usage** regularly
4. **Implement caching** where possible

### Netlify Optimizations

1. **Optimize build times** with caching
2. **Use Netlify CDN** effectively
3. **Minimize bundle size** with code splitting
4. **Monitor bandwidth usage**

### API Cost Management

1. **Implement usage limits** per client
2. **Cache responses** where possible
3. **Monitor API consumption** daily
4. **Optimize prompt engineering** for AI services

---

## 📞 Support & Resources

### Platform Documentation
- **Render**: https://render.com/docs
- **Netlify**: https://docs.netlify.com

### Useful Tools
- **Render CLI**: For advanced deployments
- **Netlify CLI**: For local development
- **Docker**: For local testing
- **Postman**: For API testing

### Emergency Contacts
- **Render Support**: support@render.com
- **Netlify Support**: support@netlify.com

---

## 🎯 Next Steps

1. **✅ Complete initial deployment**
2. **✅ Test all functionality** 
3. **✅ Set up monitoring**
4. **✅ Configure custom domains**
5. **✅ Implement backup strategy**
6. **✅ Train team on maintenance procedures**
7. **✅ Plan scaling strategy** for growth

**Estimated Total Deployment Time**: 2-3 hours for experienced developers

**Production Ready**: Yes, this setup is suitable for serving 5 clients with 1000 meeting minutes each per month. 