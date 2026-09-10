from django.core.management.base import BaseCommand
from apps.dashboard.mongo_models import _tool_privs, _TOOLS_SEED


class Command(BaseCommand):
    help = 'Force-sync requires_login from _TOOLS_SEED into MongoDB (upserts missing tools too)'

    def handle(self, *args, **options):
        col = _tool_privs()
        for slug, name, category, requires_login, icon in _TOOLS_SEED:
            result = col.update_one(
                {'slug': slug},
                {'$set': {
                    'slug': slug,
                    'name': name,
                    'category': category,
                    'requires_login': requires_login,
                    'icon': icon,
                }},
                upsert=True,
            )
            status = 'inserted' if result.upserted_id else 'updated'
            lock = 'Lock' if requires_login else 'Free'
            self.stdout.write(f'  {status}: {name} → {lock}')
        self.stdout.write(self.style.SUCCESS('Done.'))
