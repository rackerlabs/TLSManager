from django.conf.urls import patterns, url, include
#from django.views.generic import TemplateView
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    "",
    url(r'^admin/', include(admin.site.urls)),
    url(r"^endpoints/", include("TLSManager.endpoints.urls")),
)
