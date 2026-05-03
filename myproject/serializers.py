from rest_framework import serializers
from .models import Faculty, Department, LevelInfo, Course, AdmissionRequirement

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ['level_info']

class AdmissionRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionRequirement
        exclude = ['department'] 

# 👉 NEW: The Middle-Man Serializer
class LevelInfoSerializer(serializers.ModelSerializer):
    # This automatically grabs all courses assigned to this specific level
    courses = CourseSerializer(many=True, read_only=True)

    class Meta:
        model = LevelInfo
        exclude = ['department']

class DepartmentSerializer(serializers.ModelSerializer):
    faculty = FacultySerializer(read_only=True)
    admission_info = AdmissionRequirementSerializer(read_only=True)
    
    # 👉 This pulls in the LevelInfo, which brings the courses with it
    levels = LevelInfoSerializer(many=True, read_only=True)

    class Meta:
        model = Department
        fields = '__all__'