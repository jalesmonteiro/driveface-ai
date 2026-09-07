from django.urls import path
from .views import GoogleOAuthInitView, GoogleOAuthCallbackView

urlpatterns = [
    path("oauth/init/", GoogleOAuthInitView.as_view(), name="google_oauth_init"),
    path(
        "oauth/callback/",
        GoogleOAuthCallbackView.as_view(),
        name="google_oauth_callback",
    ),
]
