## Configuration

Create a `.env` file in the backend root directory.

Example:

```env
APP_NAME=AI Legal Assistance API
APP_VERSION=0.1.0
ENVIRONMENT=development

MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=legal_assistance

JWT_SECRET=your-development-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

LLM_API_KEY=

UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=10