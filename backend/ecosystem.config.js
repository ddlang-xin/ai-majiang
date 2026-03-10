module.exports = {
  apps: [
    {
      name: 'ai-majiang-backend',
      script: 'main.py',
      interpreter: 'python3',
      interpreterArgs: '-u',
      cwd: '/root/ai-projects/ai-majiang/backend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        PYTHONUNBUFFERED: '1',
        PORT: 8088
      },
      error_file: '/var/log/pm2/ai-majiang-error.log',
      out_file: '/var/log/pm2/ai-majiang-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      // 部署相关
      deploy: {
        production: {
          user: 'root',
          host: 'localhost',
          ref: 'origin/main',
          repo: 'git@github.com:your-repo/ai-majiang.git',
          path: '/var/www/ai-majiang',
          'pre-deploy-local': '',
          'post-deploy': 'cd backend && pip install -r requirements.txt && pm2 restart ecosystem.config.js'
        }
      }
    }
  ]
};
