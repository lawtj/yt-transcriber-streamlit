from pocketbase import PocketBase
import os
from dotenv import load_dotenv

load_dotenv()

client = PocketBase(os.getenv('POCKETBASE_URL'))

admin_data = client.admins.auth_with_password(os.getenv('POCKETBASE_ADMIN_EMAIL'), os.getenv('POCKETBASE_ADMIN_PASSWORD'))

try:
    print('Fetching transcript...')
    transcripts = client.collection('videos').get_first_list_item("video_id = 'doDKaKDvB30'")
except Exception as e:
    print(e)

try:
    print('Creating transcript...')
    client.collection('videos').create({
        'video_id': 'doDKaKDvB30',
        'transcript': 'test transcript',
        'summary': 'test summary'
    })
except Exception as e:
    print(e)