"""
URL configuration for fisio_project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from core.views import submit_feedback

urlpatterns = [
    path('admin/', admin.site.urls),
    path('feedback/', submit_feedback, name='feedback-submit'),
    path('', include('core.urls')),
    path('', include('painel.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('importacao/', include('importacao.urls')),
    path('forms/', include('forms.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
