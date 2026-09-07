from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class GoogleOAuthInitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"auth_url": "https://accounts.google.com/o/oauth2/v2/auth"})


class GoogleOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"message": "Callback placeholder"})
