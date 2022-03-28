from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from competitor.models import Competitor, Team
from competitor.serializer import CompetitorSerializer
from task.models import QueryTask
from task.serializer import QueryTaskSerializer


@api_view(['POST'])
def register(request):
    # change email and password
    email = request.data.get("email")
    if not User.objects.filter(email=email).exists():
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "unknown email"})
    name = request.data.get("name")
    password = request.data.get('password')
    user = User.objects.get(email=email)
    if user.password == "":
        competitor = Competitor.objects.filter(email=email).first()
        user.username = name
        user.set_password(password)
        user.save()
        return Response(status=status.HTTP_200_OK, data={"id": user.id,
                                                         "name": user.username,
                                                         "team_uuid": competitor.team.uuid,
                                                         "team_name": competitor.team.name,
                                                         "email": user.email,
                                                         "token": str(user.auth_token),
                                                         "remain_upload_times": competitor.team.remain_upload_times})
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "already registered!"})


@api_view(['POST'])
def login(request):
    # authenticate
    email = request.data.get("email")
    if not User.objects.filter(email=email).exists():
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "unknown email"})
    username = User.objects.filter(email=email).first().username
    competitor = Competitor.objects.filter(email=email).first()
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        if not user.is_superuser:
            return Response(status=status.HTTP_200_OK, data={"id": user.id,
                                                             "role": "competitor",
                                                             "name": user.username,
                                                             "team_uuid": competitor.team.uuid,
                                                             "team_name": competitor.team.name,
                                                             "email": user.email,
                                                             "token": str(user.auth_token),
                                                             "remain_upload_times": competitor.team.remain_upload_times})
        if not Token.objects.filter(user=user).exists():
            Token.objects.create(user=user)
        return Response(status=status.HTTP_200_OK, data={"id": user.id,
                                                         "role": "administrator",
                                                         "name": user.username,
                                                         "email": user.email,
                                                         "token": str(user.auth_token)})
    return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "wrong password!"})


class CompetitorViewset(viewsets.ModelViewSet):
    queryset = Competitor.objects.all()
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        # check permission
        user_id = int(kwargs.get("pk"))
        if not request.user.is_superuser and request.user.id != user_id:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"message": "permission denied!"})

        competitor_instance = Competitor.objects.get(id=user_id)

        team = competitor_instance.team
        tasks = QueryTask.objects.filter(competitor__team=team).order_by("start_time")
        tasks_serializer = QueryTaskSerializer(tasks, many=True)
        latest_task_serializer = QueryTaskSerializer(tasks.first())

        result_data = {
            "id": competitor_instance.id,
            "name": request.user.username,
            "team_uuid": competitor_instance.team.uuid,
            "team_name": competitor_instance.team.name,
            "latest_task": latest_task_serializer.data,
            "tasks": tasks_serializer.data,
            "remain_upload_times": team.remain_upload_times
        }
        return Response(status=status.HTTP_200_OK, data=result_data)

    @action(detail=True, methods=['PUT'])
    def team(self, request, *args, **kwargs):
        # check permission
        user_id = int(kwargs.get("pk"))
        if not request.user.is_superuser and request.user.id != user_id:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"message": "permission denied!"})

        # change team detail
        try:
            competitor = Competitor.objects.get(pk=kwargs.get('pk'))
            current_team = competitor.team
            current_team_uuid = competitor.team.uuid
            target_team_uuid = request.data['team_uuid']
            target_team = Team.objects.get(uuid=target_team_uuid)
            if current_team_uuid == target_team_uuid and str(current_team.name) != str(request.data['team_name']):
                Team.objects.filter(uuid=target_team_uuid).update(name=request.data['team_name'])
                # print("[Update Team Name] ", target_team.name, " -> ", request.data['team_name'])
            elif current_team_uuid != target_team_uuid and target_team.name == request.data['team_name']:
                competitor.team = target_team
                competitor.save()
                current_team.delete()
                # print("[Combine Teams] ", current_team.name, " -> ", target_team.name)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"message": "Please check the uuid or team name"})
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"message": f"Please check the uuid or team name. ERROR: {str(e)}"})

        json_data = {'id': target_team.id,
                     'name': competitor.username,
                     'team_uuid': target_team.uuid,
                     'team_name': request.data['team_name']
                     }
        if target_team.best_public_task is not None:
            task_serializer = QueryTaskSerializer(target_team.best_public_task)
            json_data['best_public_task'] = task_serializer.data
        else:
            json_data['best_public_task'] = {}
        json_data['remain_upload_times'] = target_team.remain_upload_times

        return Response(status=status.HTTP_200_OK, data=json_data)

    @action(detail=True, methods=['POST', 'GET'])
    def task(self, request, *args, **kwargs):
        # check permission
        user_id = int(kwargs.get("pk"))
        if not request.user.is_superuser and request.user.id != user_id:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"message": "permission denied!"})

        # create task
        if request.method == 'POST':

            return Response(status=status.HTTP_200_OK, data={})
        # retrieve latest task of the team
        elif request.method == 'GET':
            competitor_instance = Competitor.objects.get(pk=user_id)
            team = competitor_instance.team
            task = QueryTask.objects.filter(competitor__team=team).order_by("start_time").first()
            task_serializer = QueryTaskSerializer(task)
            return Response(status=status.HTTP_200_OK, data=task_serializer.data)
