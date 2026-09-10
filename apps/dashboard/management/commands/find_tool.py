from django.core.management.base import BaseCommand
from apps.dashboard.mongo_models import _tool_privs


class Command(BaseCommand):
    help = 'Find a tool in MongoDB by slug (or list all tools)'

    def add_arguments(self, parser):
        parser.add_argument('slug', nargs='?', default=None,
                            help='Tool slug to look up (omit to list all)')

    def handle(self, *args, **options):
        col = _tool_privs()
        slug = options.get('slug')

        if slug:
            doc = col.find_one({'slug': slug})
            if doc:
                self.stdout.write(self.style.SUCCESS(f'FOUND: {slug}'))
                for k, v in doc.items():
                    if k != '_id':
                        self.stdout.write(f'  {k}: {v}')
            else:
                self.stdout.write(self.style.ERROR(f'NOT FOUND in MongoDB: {slug}'))
        else:
            docs = list(col.find({}, {'_id': 0, 'slug': 1, 'name': 1,
                                      'category': 1, 'requires_login': 1}))
            docs.sort(key=lambda d: (d.get('category', ''), d.get('name', '')))
            self.stdout.write(f'Total tools in MongoDB: {len(docs)}\n')
            for d in docs:
                lock = 'LOCK' if d.get('requires_login') else 'free'
                self.stdout.write(f"  [{lock}]  {d.get('slug'):<30}  {d.get('name')}")
