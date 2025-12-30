from django.urls import path, include
from . import views
from . import api_urls

app_name = "gardens"

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),

    path("gardens/", views.garden_list, name="garden_list"),
    path("gardens/new/", views.garden_create, name="garden_create"),
    path("gardens/<int:garden_id>/", views.garden_detail, name="garden_detail"),

    # HTMX side panel routes
    path("gardens/<int:garden_id>/pods/<int:position>/panel/", views.pod_panel, name="pod_panel"),
    path("gardens/<int:garden_id>/pods/<int:position>/save/", views.pod_save, name="pod_save"),
    path("gardens/<int:garden_id>/pods/<int:position>/notes/add/", views.pod_note_add, name="pod_note_add"),

    # sharing
    path("gardens/<int:garden_id>/share/toggle/", views.garden_toggle_public, name="garden_toggle_public"),
    path("g/<slug:share_slug>/", views.garden_public, name="garden_public"),

    # import/export
    path("gardens/<int:garden_id>/export.json", views.garden_export_json, name="garden_export_json"),
    path("gardens/import/", views.garden_import_json, name="garden_import_json"),

    # (flip view removed) 
    # guest mode
    path("try/", views.guest_start, name="guest_start"),

    # Global notes UI
    path("gardens/notes/", views.global_notes_list_create, name="global_notes"),
    path("gardens/notes/create/", views.global_note_create, name="global_note_create"),
    path("gardens/notes/<int:pk>/delete/", views.global_note_delete, name="global_note_delete"),
    path("gardens/notes/<int:pk>/edit/", views.global_note_edit, name="global_note_edit"),

    # API
    path("api/", include(api_urls)),

]

