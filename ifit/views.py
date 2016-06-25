# -*- coding: utf-8 -*-
from requests import Response

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from rest_framework import generics
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ifit.permissions import *
from ifit.serializers import *


def index(request):
	return HttpResponse("To jest serwer aplikacji IF IT Challenge")


class UsersList(generics.ListCreateAPIView):
	serializer_class = UserSerializer
	permission_classes = (IsThisUserOrSuperUser,)

	def get_queryset(self):
		user = self.request.user
		if not isinstance(user, AnonymousUser):
			return User.objects.filter(id=user.id)
		raise PermissionDenied


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = (IsThisUserOrSuperUser,)


class GroupsList(generics.ListCreateAPIView):
	queryset = Group.objects.all()
	serializer_class = GroupSerializer
	permission_classes = (IsOwnerOrReadOnly,)


class GroupDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = Group.objects.all()
	serializer_class = GroupSerializer
	permission_classes = (IsOwnerOrReadOnly,)


class ChallengeList(generics.ListCreateAPIView):
	serializer_class = ChallengeSerializer
	permission_classes = (IsOwner,)

	def get_queryset(self):
		user = self.request.user
		if isinstance(user, AnonymousUser):
			raise PermissionDenied
		return Challenge.objects.filter(owner=user.profile)


class ChallengeDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = Challenge.objects.all()
	serializer_class = ChallengeSerializer


class ChallengeDataList(generics.ListAPIView):
	queryset = ChallengeData.objects.all()
	serializer_class = ChallengeDataSerializer
	permission_classes = (IsChallenged,)

	def get_queryset(self):
		user = self.request.user
		if isinstance(user, AnonymousUser):
			raise PermissionDenied
		return ChallengeData.objects.filter(challenged=user.profile)


class ChallengeDataDetail(generics.RetrieveAPIView):
	queryset = ChallengeData.objects.all()
	serializer_class = ChallengeDataSerializer
	permission_classes = (IsChallengedOrOwner,)


class ProfilesList(generics.ListCreateAPIView):
	queryset = Profile.objects.all()
	serializer_class = ProfileSerializer

	def get_queryset(self):
		user = self.request.user
		if not isinstance(user, AnonymousUser):
			return Profile.objects.filter(user=user)
		raise PermissionDenied


class ProfileDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = Profile.objects.all()
	serializer_class = ProfileSerializer


class FriendRequestList(generics.ListCreateAPIView):
	queryset = FriendRequest.objects.all()
	serializer_class = FriendRequestSerializer

	def get_queryset(self):
		user = self.request.user
		profile = user.profile
		if not isinstance(user, AnonymousUser):
			return FriendRequest.objects.filter(Q(requester=profile) | Q(friend=profile))
		raise PermissionDenied


class FriendRequestDetail(generics.RetrieveAPIView):
	queryset = FriendRequest.objects.all()
	serializer_class = FriendRequestSerializer


class ChallengeViewSet(ModelViewSet):
	queryset = Challenge.objects.all()
	serializer_class = ChallengeSerializer

	@detail_route(methods=['GET'])
	def get_challenged(self, request, pk=None):
		if not isinstance(request.user, AnonymousUser):
			challenge = self.get_object()
			challenge_data = ChallengeData.objects.filter(challenge=challenge).values_list('challenged', flat=True)
			profiles = Profile.objects.filter(id__in=challenge_data)
			challenged = [
				{'username': p.username, 'id': p.id, 'user': p.user.id, 'avatar': p.avatar.url if p.avatar else None}
				for p in profiles]
			return JsonResponse(list(challenged), safe=False)
		raise PermissionDenied

	@detail_route(methods=['POST'])
	def add_to_challenge(self, request, pk=None):
		if not isinstance(request.user, AnonymousUser):
			challenge = self.get_object()
			me = request.user.profile
			if 'challenged' in request.POST:
				challenged = request.POST["challenged"]
				challenged = [c for c in challenged.split()]
				challenge_data = ChallengeData.objects.filter(challenge=challenge).values_list('challenged__id',
				                                                                               flat=True)
				friends = me.friends.all().values_list('id', flat=True)
				profiles = Profile.objects.filter(id__in=challenged).exclude(id__in=challenge_data).exclude(
					id__in=friends)
				added = 0
				for profile in profiles:
					new_challenge_data = ChallengeData(challenge=challenge, challenged=profile)
					new_challenge_data.save()
					added += 1
				return JsonResponse({'added': added})
			else:
				return JsonResponse({'error': 'Missing parameter <challenged>'})
		raise PermissionDenied
