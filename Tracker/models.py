from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Cycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cycles')  # ADD THIS LINE
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    cycle_length = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"Cycle starting {self.start_date} - {self.user.username}"

    def calculate_cycle_length(self):
        if self.end_date:
            self.cycle_length = (self.end_date - self.start_date).days
            self.save()

class DailyLog(models.Model):
    FLOW_CHOICES = [
        ('none', 'None'),
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy'),
    ]

    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField()
    flow_intensity = models.CharField(max_length=10, choices=FLOW_CHOICES, default='none')
    
    # Symptoms
    cramps = models.BooleanField(default=False)
    headache = models.BooleanField(default=False)
    mood_swings = models.BooleanField(default=False)
    fatigue = models.BooleanField(default=False)
    bloating = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['cycle', 'date']

    def __str__(self):
        return f"Log for {self.date}"