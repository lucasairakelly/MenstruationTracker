from django.contrib import admin
from django.urls import path
from Tracker import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    
    # Main URLs (protected)
    path('', views.home, name='home'),
    
    # Cycle CRUD
    path('cycles/create/', views.cycle_create, name='cycle_create'),
    path('cycles/<int:pk>/', views.cycle_detail, name='cycle_detail'),
    path('cycles/<int:pk>/update/', views.cycle_update, name='cycle_update'),
    path('cycles/<int:pk>/delete/', views.cycle_delete, name='cycle_delete'),
    
    # Daily Log CRUD
    path('cycles/<int:cycle_pk>/logs/add/', views.daily_log_create, name='daily_log_create'),
    path('cycles/<int:cycle_pk>/logs/<int:log_pk>/update/', views.daily_log_update, name='daily_log_update'),
    path('cycles/<int:cycle_pk>/logs/<int:log_pk>/delete/', views.daily_log_delete, name='daily_log_delete'),
    
    # Forecast API
    path('api/forecast/', views.forecast_view, name='forecast_api'),

    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
]