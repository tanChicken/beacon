from django.shortcuts import render, HttpResponse
from .models import TodoItem

# Create your views here.
def home(request):
    return render(request, "home.html")

# def todos(request):
#     items =  TodoItem.objects.all()
#     return render(request, "todos.html", {"todos":items})

def create_edit_course(request):
    return render(request, "create_edit_courses.html")

def login(request):
    return render(request, "login.html")

def sign_up(request):
    return render(request, "singup.html")
