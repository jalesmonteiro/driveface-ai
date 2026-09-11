from django.urls import path
from .views import GoogleOAuthInitView, GoogleOAuthCallbackView, GoogleDriveFoldersView

urlpatterns = [
    path("oauth/init/", GoogleOAuthInitView.as_view(), name="google_oauth_init"),
    path("oauth/url/", GoogleOAuthInitView.as_view(), name="google_oauth_url"),
    path(
        "oauth/callback/",
        GoogleOAuthCallbackView.as_view(),
        name="google_oauth_callback",
    ),
    path(
        "drive/folders/",
        GoogleDriveFoldersView.as_view(),
        name="google_drive_folders",
    ),
]

