from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import DemoLoginView, RegisterView, UserProfileView
 
urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("demo-login/", DemoLoginView.as_view(), name="auth_demo_login"),
    path("me/", UserProfileView.as_view(), name="auth_me"),
]
