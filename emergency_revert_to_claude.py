#!/usr/bin/env python3
"""
Emergency Revert: Switch back to Claude Sonnet 3.7 for critical AI functions
Run this on Coolify to fix production issues immediately
"""

def revert_to_claude():
    print('🚨 EMERGENCY REVERT: Switching back to Claude Sonnet 3.7')
    print('=' * 60)
    
    # Files to update
    files_to_update = [
        'app/utils/ai/keyword_extraction_service.py',
        'app/news/routes.py', 
        'app/utils/scheduler/news_scheduler.py'
    ]
    
    # Model replacements
    replacements = {
        'deepseek/deepseek-chat-v3-0324:free': 'anthropic/claude-3.7-sonnet',
        'deepseek/deepseek-r1-0528-qwen3-8b:free': 'anthropic/claude-3.7-sonnet'
    }
    
    for file_path in files_to_update:
        try:
            print(f'\n📝 Updating {file_path}...')
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Replace DeepSeek models with Claude
            for old_model, new_model in replacements.items():
                if old_model in content:
                    content = content.replace(old_model, new_model)
                    print(f'   ✅ Replaced {old_model} → {new_model}')
            
            # Reduce token limits back to Claude's conservative limits
            if 'max_tokens=750' in content:
                content = content.replace('max_tokens=750', 'max_tokens=500')
                print('   ⚙️  Reduced max_tokens: 750 → 500')
                
            if 'max_tokens=8000' in content:
                content = content.replace('max_tokens=8000', 'max_tokens=4000')
                print('   ⚙️  Reduced input limit: 8000 → 4000')
                
            if 'max_tokens=10000' in content:
                content = content.replace('max_tokens=10000', 'max_tokens=4000')
                print('   ⚙️  Reduced input limit: 10000 → 4000')
            
            # Write changes if any were made
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print('   ✅ File updated successfully')
            else:
                print('   ℹ️  No changes needed')
                
        except Exception as e:
            print(f'   ❌ Error updating {file_path}: {str(e)}')
    
    print('\n' + '=' * 60)
    print('✅ REVERT COMPLETE - Claude Sonnet 3.7 restored')
    print('\n🔄 Next steps:')
    print('1. Restart your application on Coolify')
    print('2. Test sentiment analysis and insights generation') 
    print('3. Verify all AI functions work properly')
    print('\n💡 Future: Consider hybrid approach or wait for DeepSeek improvements')

if __name__ == '__main__':
    revert_to_claude() 