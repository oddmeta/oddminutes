from django.core.management.base import BaseCommand
from summary.models import SummaryTemplate, SummaryLanguagePreference


class Command(BaseCommand):
    help = 'Initialize default data'

    def handle(self, *args, **options):
        # 创建默认摘要模板
        default_template, created = SummaryTemplate.objects.get_or_create(
            name='标准会议模板',
            defaults={
                'description': '包含会议目标、决策、行动项等标准结构',
                'structure': {
                    'sections': [
                        '会议目标',
                        '参会人员',
                        '会议概要',
                        '关键决策',
                        '行动项',
                        '后续步骤',
                    ]
                },
                'is_default': True,
                'is_builtin': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created template: {default_template.name}'))

        # 创建语言偏好
        lang_pref, created = SummaryLanguagePreference.objects.get_or_create(
            language='zh',
            defaults={
                'language_name': '中文',
                'is_default': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created language preference: {lang_pref.language_name}'))

        self.stdout.write(self.style.SUCCESS('Default data initialized'))
