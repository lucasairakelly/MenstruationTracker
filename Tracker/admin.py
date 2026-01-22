from django.contrib import admin
from .models import Cycle, DailyLog

@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'end_date', 'cycle_length', 'created_at']
    list_filter = ['start_date']
    search_fields = ['notes']

@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['date', 'cycle', 'flow_intensity', 'cramps', 'headache']
    list_filter = ['date', 'flow_intensity']
    search_fields = ['notes']
