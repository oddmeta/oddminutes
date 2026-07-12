from django.db import models
from core.models import BaseModel


class SummaryTemplate(BaseModel):
    """摘要模板"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    structure = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    is_builtin = models.BooleanField(default=False)

    class Meta:
        db_table = 'summary_templates'

    def __str__(self):
        return self.name


class AIModelConfig(BaseModel):
    """AI 模型配置"""
    provider = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=500, blank=True)
    base_url = models.URLField(blank=True)
    is_default = models.BooleanField(default=False)
    extra_params = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'ai_model_configs'

    def __str__(self):
        return f"{self.provider}/{self.model_name}"


class SummaryLanguagePreference(BaseModel):
    """摘要语言偏好"""
    language = models.CharField(max_length=10, default='zh')
    language_name = models.CharField(max_length=50, default='中文')
    is_default = models.BooleanField(default=True)

    class Meta:
        db_table = 'summary_language_preferences'
