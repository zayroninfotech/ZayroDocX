from django.core.management.base import BaseCommand
from apps.dashboard.mongo_models import _tool_privs


class Command(BaseCommand):
    help = 'Remove specific tools from MongoDB tool_privileges collection'

    def handle(self, *args, **options):
        col = _tool_privs()
        slugs = ['meme-generator', 'upscale-image']
        for slug in slugs:
            result = col.delete_one({'slug': slug})
            if result.deleted_count:
                self.stdout.write(self.style.SUCCESS(f'Deleted: {slug}'))
            else:
                self.stdout.write(f'Not found: {slug}')
