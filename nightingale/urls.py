from django.contrib import admin
from django.urls import include, path


admin.site.site_header = "Nightingale Staff Portal"
admin.site.site_title = "Nightingale Staff"
admin.site.index_title = "Clinic Operations"


urlpatterns = [
    path("staff/", admin.site.urls),
    path("", include("core.urls")),
]