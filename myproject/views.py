from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import MultipleObjectsReturned
from fuzzywuzzy import process, fuzz
from django.http import JsonResponse
from django.views import View
from .models import Faculty, Department, Course
from .serializers import FacultySerializer, DepartmentSerializer, CourseSerializer

def chat(request):
    return render(request, 'chat.html')

class DepartmentSearchAPI(APIView):
    def get(self, request, query_name):
        try:
            all_depts = Department.objects.all()
            if not all_depts.exists():
                return Response({"error": "The department database is empty."}, status=status.HTTP_404_NOT_FOUND)
            
            names_list = [d.name for d in all_depts]
            best_match, score = process.extractOne(query_name, names_list, scorer=fuzz.ratio)

            if score >= 80:
                dept = Department.objects.get(name=best_match)
                # This single line triggers the massive nested JSON payload
                serializer = DepartmentSerializer(dept)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": f"I couldn't find a department matching '{query_name}'."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": "An error occurred on the server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FacultySearchAPI(View):
    def get(self, request, query_name, *args, **kwargs):
        try:
            # 1. Search for the faculty using the exact variable name from your urls.py
            faculty = Faculty.objects.get(name__iexact=query_name)
            
            # 2. Find all departments that belong to this specific faculty
            departments = Department.objects.filter(faculty=faculty)
            
            # 3. Format the departments into a simple list of dictionaries
            dept_list = [{"name": dept.name} for dept in departments]
            
            # 4. Build the exact JSON package Rasa is expecting
            data = {
                "name": faculty.name,
                "dean": faculty.dean, 
                "about": faculty.about,
                "departments": dept_list
            }
            
            return JsonResponse(data, status=200)
            
        except Faculty.DoesNotExist:
            return JsonResponse({"error": f"Faculty '{query_name}' not found."}, status=404)

class CourseSearchAPI(APIView):
    def get(self, request, course_code):
        try:
            # 1. Try an exact, case-insensitive match first (e.g., exactly what Rasa sent)
            course = Course.objects.filter(course_code__iexact=course_code).first()
            
            # 2. If not found, standardise it: Strip all spaces and make uppercase
            input_clean = course_code.replace(" ", "").upper()
            
            if not course:
                # Try searching the database for the spaceless version (e.g., "CSC411")
                course = Course.objects.filter(course_code__iexact=input_clean).first()
                
            if not course and len(input_clean) >= 6:
                # Try injecting a standard space (e.g., turning "CSC411" into "CSC 411")
                # This splits the first 3 letters from the numbers
                spaced_code = input_clean[:3] + " " + input_clean[3:]
                course = Course.objects.filter(course_code__iexact=spaced_code).first()

            # 3. Final Check: Did any of our 3 attempts work?
            if course:
                serializer = CourseSerializer(course)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": f"Course '{course_code}' not found in the database."}, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({"error": "An error occurred on the server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)