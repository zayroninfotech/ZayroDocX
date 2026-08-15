from django.core.management.base import BaseCommand
from apps.dashboard.mongo_models import _tool_privs, _TOOLS_SEED, count_tools


class Command(BaseCommand):
    help = 'Sync all tools to MongoDB tool_privileges collection'

    def handle(self, *args, **options):
        col = _tool_privs()
        created = 0
        for slug, name, category, requires_login, icon in _TOOLS_SEED:
            existing = col.find_one({'slug': slug})
            if existing:
                col.update_one({'slug': slug}, {'$set': {'name': name, 'category': category, 'icon': icon}})
            else:
                col.insert_one({'slug': slug, 'name': name, 'category': category,
                                'requires_login': requires_login, 'icon': icon})
                created += 1
                self.stdout.write(f'  + Added: {name}')
        total = count_tools()
        self.stdout.write(self.style.SUCCESS(
            f'Done. {created} new tools added. {total} total tools in MongoDB.'
        ))
