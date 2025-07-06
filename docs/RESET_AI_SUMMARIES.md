# Reset AI Summaries Feature

## Overview

The Reset AI Summaries feature allows you to reset the AI-generated content for the latest N articles, making them available for reprocessing with updated AI models or improved layout formatting.

## How to Use

### Via Web Interface

1. **Navigate to News Fetch Page**
   - Go to `/news/fetch` in your application
   - You'll see a red "Reset AI Summaries" button in the action bar

2. **Reset Process**
   - Click the "Reset AI Summaries" button
   - Enter the number of latest articles you want to reset (default: 10)
   - Confirm the action when prompted
   - The system will reset AI summaries for the specified number of articles

3. **What Gets Reset**
   - `ai_summary` field → set to `NULL`
   - `ai_insights` field → set to `NULL` 
   - `ai_sentiment_rating` field → set to `NULL`
   - `ai_processed_at` field → set to `NULL`

### Via API

**Endpoint:** `POST /news/api/reset-ai-summaries`

**Request Body:**
```json
{
    "num_articles": 10
}
```

**Response:**
```json
{
    "success": true,
    "reset_count": 10,
    "message": "Successfully reset AI summaries for 10 articles"
}
```

## Use Cases

### 1. Layout Problem Fix
When you've updated the AI summary layout format (like the recent structured layout with AI Summary and AI Insights sections), you can reset articles to reprocess them with the new format.

### 2. AI Model Updates
When you've improved your AI prompts or switched to a better AI model, reset articles to get better quality summaries.

### 3. Content Quality Issues
If you notice poor quality AI summaries in recent articles, reset them for reprocessing.

### 4. Testing and Development
Reset a small number of articles (e.g., 5-10) to test new AI processing logic.

## Safety Features

- **Confirmation Required**: The web interface requires user confirmation before resetting
- **Input Validation**: Only positive integers are accepted for the number of articles
- **Targeted Reset**: Only articles that actually have AI content are affected
- **Latest First**: Articles are selected by most recent publication date
- **Database Rollback**: If an error occurs, database changes are rolled back

## After Reset

Once articles are reset:

1. **Automatic Reprocessing**: The automated news scheduler will pick up these articles in its next run (every 30 minutes)
2. **Manual Reprocessing**: You can trigger immediate reprocessing using the "Update AI Summaries" button
3. **Status Tracking**: Reset articles will show as "pending AI processing" in the system

## Technical Details

### Database Query
```sql
SELECT * FROM news_articles 
WHERE (ai_summary IS NOT NULL OR ai_insights IS NOT NULL OR ai_sentiment_rating IS NOT NULL)
ORDER BY published_at DESC 
LIMIT :num_articles
```

### Reset Operation
```sql
UPDATE news_articles 
SET ai_summary = NULL, 
    ai_insights = NULL, 
    ai_sentiment_rating = NULL, 
    ai_processed_at = NULL
WHERE id IN (selected_article_ids)
```

## Monitoring

- **Logs**: All reset operations are logged with the number of articles affected
- **UI Feedback**: Success/failure messages are displayed in the web interface
- **Error Handling**: Database errors are caught and reported appropriately

## Best Practices

1. **Start Small**: Test with 5-10 articles before resetting larger batches
2. **Monitor Processing**: Check that articles are being reprocessed correctly after reset
3. **Backup Consideration**: Consider backing up AI content before major resets
4. **Timing**: Reset during low-traffic periods to avoid impacting users

## Troubleshooting

### No Articles Reset
- Check if the specified articles actually have AI content
- Verify database connectivity
- Check application logs for errors

### Partial Reset
- Database transaction may have been interrupted
- Check logs for specific error messages
- Some articles may have been processed successfully

### Reprocessing Not Working
- Verify the automated scheduler is running
- Check AI service availability
- Manually trigger "Update AI Summaries" if needed 