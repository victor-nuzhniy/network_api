"""Class and function views for 'api' app."""
from datetime import datetime

from django.db.models import Count, F
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Like, Post, User
from .schemas import LikeSchema, analitics_schema, user_register_schema
from .serializers import LikeSerializer, PostSerializer, UserSerializer
from .services.model_operations import get_like_instance


class RegisterView(APIView):
    """Class view for user registering."""

    schema = user_register_schema

    @staticmethod
    def post(self, request: Request) -> Response:
        """Post data to create User."""
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PostCreateView(generics.CreateAPIView):
    """Class with only POST method for creating message (post)."""

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def perform_create(self, serializer) -> None:
        """Add user to serializer and save Post instance."""
        serializer.save(user=self.request.user)


class LikeView(APIView):
    """Class with only POST method for creating Like with eval = True."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    schema = LikeSchema()

    @staticmethod
    def post(request, format=None) -> Response:
        """
        Create Like instance.

        If "eval" has value "Like", instance saves "eval" field with True.
        "Dislike" - False.
        Otherwise - Response with "Invalid input data.".
        """
        message_id: int = request.data.get("message_id")
        user: User = request.user
        eval_data = request.data.get("eval").lower()
        if eval_data == "like":
            like: bool = True
        elif eval_data == "dislike":
            like = False
        else:
            return Response(
                {"result": "Invalid input data."}, status=status.HTTP_406_NOT_ACCEPTABLE
            )
        serializer = LikeSerializer(
            data={
                "user": user.pk,
                "message": message_id,
                "eval": like,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @staticmethod
    def delete(request, format=None) -> Response:
        """Delete Like instance."""
        if like := get_like_instance(request.user, request.data.get("message_id")):
            like.delete()
            return Response({"result": "Like was successfully deleted."})
        return Response(
            {"result": "Like was not found"}, status=status.HTTP_404_NOT_FOUND
        )


class AnaliticView(APIView):
    """Class for view with like analitic."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    schema = analitics_schema

    @staticmethod
    def get(request: Request, format=None) -> Response:
        """
        Handle input and return analitics data.

        Input format - '%Y-%m-%d'.
        Return list with dates and likes per date in given range.
        """
        try:
            date_from = datetime.strptime(
                request.query_params.get("date_from"), "%Y-%m-%d"
            )
            date_to = datetime.strptime(request.query_params.get("date_to"), "%Y-%m-%d")
        except ValueError:
            return Response(
                {"result": "Invalid input format."},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        data = (
            Like.objects.filter(created_at__range=(date_from, date_to))
            .annotate(date=F("created_at__date"))
            .values("date")
            .order_by("date")
            .annotate(likes=Count("eval"))
        )

        return Response({"analitics": list(data)})
