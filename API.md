# 📡 StreamFlix Bot API Documentation

Complete API reference for StreamFlix Bot's REST endpoints and Telegram bot commands.

## 🔐 Authentication

### JWT Token Authentication
Most API endpoints require JWT token authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

### Token Types
- **Admin Token**: For admin panel access and management operations
- **Stream Token**: For secure file streaming access
- **Download Token**: For secure file download access

## 🤖 Telegram Bot Commands

### User Commands

#### `/start`
**Description**: Welcome message and user status  
**Usage**: `/start`  
**Response**: Welcome message with user status and available commands

#### `/help`
**Description**: Detailed help and feature overview  
**Usage**: `/help`  
**Response**: Comprehensive guide with all features and commands

#### `/search <query>`
**Description**: Search for files by name  
**Usage**: `/search movie.mp4`  
**Parameters**:
- `query`: Search term (filename, partial name)
**Response**: Interactive search results with stream/download buttons

#### `/request_access <name> | <purpose>`
**Description**: Request access to the bot  
**Usage**: `/request_access John Doe | Educational content sharing`  
**Parameters**:
- `name`: Full name
- `purpose`: Reason for access request
**Response**: Confirmation message and admin notification

### Admin Commands

#### `/view_users`
**Description**: List all registered users  
**Usage**: `/view_users`  
**Access**: Admin only  
**Response**: Formatted list of users with status

#### `/approve_requests`
**Description**: View pending access requests  
**Usage**: `/approve_requests`  
**Access**: Admin only  
**Response**: Interactive list of pending requests with approve/reject buttons

#### `/revoke_access @username`
**Description**: Revoke user access  
**Usage**: `/revoke_access @johndoe`  
**Access**: Admin only  
**Response**: Confirmation of access revocation

#### `/make_admin @username`
**Description**: Promote user to admin  
**Usage**: `/make_admin @johndoe`  
**Access**: Admin only  
**Response**: Confirmation of role change

#### `/remove_admin @username`
**Description**: Demote admin to user  
**Usage**: `/remove_admin @johndoe`  
**Access**: Admin only  
**Response**: Confirmation of role change

#### `/stats`
**Description**: View bot usage statistics  
**Usage**: `/stats`  
**Access**: Admin only  
**Response**: Comprehensive usage statistics

## 🌐 REST API Endpoints

### Admin Authentication

#### POST `/admin/login`
**Description**: Authenticate admin user and get JWT token  
**Authentication**: None required  

**Request Body**:
```json
{
  "telegram_id": 123456789
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "admin",
    "role": "admin",
    "is_approved": true
  }
}
```

**Error Responses**:
- `400`: Missing telegram_id
- `403`: Invalid admin credentials

### User Management

#### GET `/admin/users`
**Description**: Get paginated list of users  
**Authentication**: Admin token required  

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)
- `search` (optional): Search term for username/name

**Response**:
```json
{
  "users": [
    {
      "id": 1,
      "telegram_id": 123456789,
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "role": "user",
      "is_approved": true,
      "created_at": "2024-01-01T00:00:00",
      "last_active": "2024-01-15T12:30:00"
    }
  ],
  "total": 50,
  "pages": 3,
  "current_page": 1
}
```

#### PUT `/admin/users/{user_id}`
**Description**: Update user details  
**Authentication**: Admin token required  

**Request Body**:
```json
{
  "is_approved": true,
  "role": "admin"
}
```

**Response**:
```json
{
  "message": "User updated successfully",
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "johndoe",
    "role": "admin",
    "is_approved": true
  }
}
```

#### DELETE `/admin/users/{user_id}`
**Description**: Revoke user access (soft delete)  
**Authentication**: Admin token required  

**Response**:
```json
{
  "message": "User access revoked successfully"
}
```

### Access Request Management

#### GET `/admin/access-requests`
**Description**: Get access requests  
**Authentication**: Admin token required  

**Query Parameters**:
- `status` (optional): Filter by status (pending, approved, rejected, all)
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Response**:
```json
{
  "requests": [
    {
      "id": 1,
      "user_id": 2,
      "name": "John Doe",
      "purpose": "Educational content sharing",
      "status": "pending",
      "requested_at": "2024-01-01T00:00:00",
      "user": {
        "id": 2,
        "telegram_id": 987654321,
        "username": "johndoe"
      }
    }
  ],
  "total": 5,
  "pages": 1,
  "current_page": 1
}
```

#### POST `/admin/access-requests/{request_id}/approve`
**Description**: Approve access request  
**Authentication**: Admin token required  

**Response**:
```json
{
  "message": "Access request approved successfully",
  "request": {
    "id": 1,
    "status": "approved",
    "processed_at": "2024-01-15T12:30:00"
  }
}
```

#### POST `/admin/access-requests/{request_id}/reject`
**Description**: Reject access request  
**Authentication**: Admin token required  

**Request Body**:
```json
{
  "notes": "Insufficient information provided"
}
```

**Response**:
```json
{
  "message": "Access request rejected successfully",
  "request": {
    "id": 1,
    "status": "rejected",
    "processed_at": "2024-01-15T12:30:00",
    "admin_notes": "Insufficient information provided"
  }
}
```

### File Management

#### GET `/admin/files`
**Description**: Get paginated list of files  
**Authentication**: Admin token required  

**Query Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page
- `search` (optional): Search filename
- `type` (optional): Filter by file type
- `uploader_id` (optional): Filter by uploader

**Response**:
```json
{
  "files": [
    {
      "id": 1,
      "filename": "abc123.mp4",
      "original_filename": "movie.mp4",
      "file_size": 1048576000,
      "file_type": "video",
      "mime_type": "video/mp4",
      "duration": 7200.5,
      "width": 1920,
      "height": 1080,
      "uploader_id": 1,
      "uploaded_at": "2024-01-01T00:00:00",
      "download_count": 15,
      "stream_count": 42,
      "uploader": {
        "id": 1,
        "username": "admin",
        "first_name": "Admin"
      }
    }
  ],
  "total": 100,
  "pages": 5,
  "current_page": 1
}
```

#### DELETE `/admin/files/{file_id}`
**Description**: Delete file  
**Authentication**: Admin token required  

**Response**:
```json
{
  "message": "File deleted successfully"
}
```

### Statistics

#### GET `/admin/stats`
**Description**: Get comprehensive system statistics  
**Authentication**: Admin token required  

**Response**:
```json
{
  "overview": {
    "total_users": 150,
    "approved_users": 120,
    "admin_users": 5,
    "total_files": 500,
    "total_downloads": 2500,
    "total_streams": 8000,
    "pending_requests": 3
  },
  "file_types": {
    "video": {
      "count": 200,
      "total_size": 50000000000
    },
    "audio": {
      "count": 150,
      "total_size": 5000000000
    },
    "document": {
      "count": 100,
      "total_size": 1000000000
    }
  },
  "recent_activity": {
    "recent_uploads": 25,
    "recent_users": 10
  },
  "top_uploaders": [
    {
      "user_id": 1,
      "username": "admin",
      "file_count": 50,
      "total_size": 10000000000
    }
  ],
  "popular_files": [
    {
      "id": 1,
      "original_filename": "popular_movie.mp4",
      "total_access": 100,
      "uploader": {
        "username": "admin"
      }
    }
  ]
}
```

### Access Logs

#### GET `/admin/access-logs`
**Description**: Get access logs  
**Authentication**: Admin token required  

**Query Parameters**:
- `page` (optional): Page number
- `per_page` (optional): Items per page (default: 50)
- `file_id` (optional): Filter by file ID
- `user_id` (optional): Filter by user ID
- `action` (optional): Filter by action (stream, download, view)

**Response**:
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 2,
      "file_id": 1,
      "action": "stream",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "accessed_at": "2024-01-15T12:30:00",
      "success": true,
      "user": {
        "username": "johndoe",
        "first_name": "John"
      },
      "file": {
        "original_filename": "movie.mp4"
      }
    }
  ],
  "total": 1000,
  "pages": 20,
  "current_page": 1
}
```

### Streaming Sessions

#### GET `/admin/streaming-sessions`
**Description**: Get active streaming sessions  
**Authentication**: Admin token required  

**Query Parameters**:
- `active_only` (optional): Show only active sessions (default: true)

**Response**:
```json
{
  "sessions": [
    {
      "id": 1,
      "user_id": 2,
      "file_id": 1,
      "session_token": "abc123...",
      "started_at": "2024-01-15T12:00:00",
      "last_position": 1800.5,
      "expires_at": "2024-01-15T18:00:00",
      "is_active": true,
      "ip_address": "192.168.1.100",
      "user": {
        "username": "johndoe"
      },
      "file": {
        "original_filename": "movie.mp4"
      }
    }
  ]
}
```

#### POST `/admin/streaming-sessions/{session_token}/revoke`
**Description**: Revoke streaming session  
**Authentication**: Admin token required  

**Response**:
```json
{
  "message": "Session revoked successfully"
}
```

### System Maintenance

#### POST `/admin/cleanup`
**Description**: Clean up expired sessions and old logs  
**Authentication**: Admin token required  

**Response**:
```json
{
  "message": "System cleanup completed",
  "deleted_logs": 150
}
```

## 🎬 Streaming API Endpoints

### File Streaming

#### GET `/stream/{jwt_token}`
**Description**: Stream file with Netflix-like player  
**Authentication**: Valid stream token required  

**Response**: HTML5 video/audio player interface

#### GET `/download/{jwt_token}`
**Description**: Download file directly  
**Authentication**: Valid download token required  

**Response**: File download with proper headers

#### GET `/api/stream/{jwt_token}/data`
**Description**: Get file data for streaming (supports range requests)  
**Authentication**: Valid stream token required  

**Headers**:
- `Range` (optional): Byte range for partial content

**Response**: File data with appropriate headers for streaming

#### POST `/api/stream/{jwt_token}/position`
**Description**: Update current playback position  
**Authentication**: Valid stream token required  

**Request Body**:
```json
{
  "position": 1800.5
}
```

**Response**:
```json
{
  "status": "success"
}
```

#### GET `/api/stream/{jwt_token}/position`
**Description**: Get current playback position  
**Authentication**: Valid stream token required  

**Response**:
```json
{
  "position": 1800.5
}
```

### File Thumbnails

#### GET `/thumbnail/{file_id}`
**Description**: Get file thumbnail  
**Authentication**: None required  

**Response**: JPEG image data

## 🔧 Error Handling

### Standard Error Response Format
```json
{
  "error": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 500 | Internal Server Error |

### Common Error Scenarios

#### Authentication Errors
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Insufficient permissions

#### Validation Errors
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found

#### Server Errors
- `500 Internal Server Error`: Unexpected server error

## 📝 Request/Response Examples

### Complete File Upload Flow

1. **Upload file via Telegram bot**
   - Send file to bot
   - Bot processes and stores file
   - Returns secure links

2. **Generate streaming link**
   ```python
   # In bot code
   stream_link = auth_service.generate_stream_link(file_id, user_id)
   # Returns: https://domain.com/stream/eyJhbGciOiJIUzI1NiIs...
   ```

3. **Access streaming player**
   ```http
   GET /stream/eyJhbGciOiJIUzI1NiIs...
   ```
   Returns HTML5 player interface

4. **Stream file data**
   ```http
   GET /api/stream/eyJhbGciOiJIUzI1NiIs.../data
   Range: bytes=0-1023
   ```
   Returns partial file content

### Admin Panel Workflow

1. **Admin login**
   ```http
   POST /admin/login
   Content-Type: application/json
   
   {
     "telegram_id": 123456789
   }
   ```

2. **Get pending requests**
   ```http
   GET /admin/access-requests?status=pending
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

3. **Approve request**
   ```http
   POST /admin/access-requests/1/approve
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

## 🔒 Security Considerations

### Token Security
- All tokens have expiration times
- Stream tokens: 6 hours
- Download tokens: 1 hour
- Admin tokens: 24 hours

### Rate Limiting
- Implement rate limiting for API endpoints
- Monitor for suspicious activity
- Log all access attempts

### Input Validation
- All inputs are validated and sanitized
- File type restrictions enforced
- Size limits implemented

### CORS Policy
- Configured for cross-origin requests
- Restricted to trusted domains in production

---

This API documentation covers all available endpoints and their usage. For implementation examples and additional details, refer to the source code and README.md file.

