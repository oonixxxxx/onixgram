import shutil
from datetime import datetime
import os

def backup_database():
    """Создание резервной копии базы данных"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source = 'instance/twitter_clone.db'
    backup_dir = 'backups'
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    destination = f'{backup_dir}/twitter_clone_{timestamp}.db'
    
    try:
        shutil.copy2(source, destination)
        print(f"Резервная копия создана: {destination}")
    except Exception as e:
        print(f"Ошибка при создании резервной копии: {e}")

if __name__ == '__main__':
    backup_database() 