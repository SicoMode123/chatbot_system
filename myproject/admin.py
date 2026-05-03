from django.contrib import admin
from .models import Faculty, Department, LevelInfo, Course, AdmissionRequirement

# ==========================================
# 1. FACULTY ADMIN
# ==========================================
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'dean', 'contact_email')
    search_fields = ('name', 'dean')


# ==========================================
# 2. DEPARTMENT ADMIN
# ==========================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'head_of_department')
    list_filter = ('faculty',)
    search_fields = ('name', 'head_of_department')


# ==========================================
# 3. LEVEL INFO ADMIN (NEW!)
# ==========================================
@admin.register(LevelInfo)
class LevelInfoAdmin(admin.ModelAdmin):
    list_display = ('department', 'level', 'course_advisor', 'special_status')
    list_filter = ('level', 'special_status', 'department')
    # Allows you to search by the Department's name or the Advisor's name
    search_fields = ('department__name', 'course_advisor', 'class_rep_name')


# ==========================================
# 4. COURSE ADMIN (Upgraded for V2)
# ==========================================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    # Added 'semester' to the display columns
    list_display = ('course_code', 'title', 'level_info', 'semester', 'credit_units', 'is_compulsory')
    
    # Added 'semester' to the filter sidebar!
    list_filter = ('level_info__department', 'level_info__level', 'semester', 'is_compulsory')
    search_fields = ('course_code', 'title', 'level_info__department__name')


# ==========================================
# 5. ADMISSION REQUIREMENTS ADMIN (Upgraded with Fieldsets)
# ==========================================
@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(admin.ModelAdmin):
    list_display = ('department', 'jamb_cutoff_mark', 'total_school_fees', 'nuc_accreditation_status', 'is_currently_admitting')
    list_filter = ('is_currently_admitting', 'nuc_accreditation_status', 'accepts_direct_entry')
    search_fields = ('department__name',)

    # 👉 THE ARCHITECT'S TOUCH: Grouping fields into clean sections in the Admin UI
    fieldsets = (
        ('Target Department', {
            'fields': ('department',)
        }),
        ('UTME Candidates (100 Level)', {
            'fields': ('jamb_cutoff_mark', 'jamb_subject_combination', 'compulsory_olevel_subjects', 'accepts_two_sittings', 'requires_math_credit', 'post_utme_screening', 'requires_first_choice'),
            'classes': ('collapse',) # Makes the section collapsible
        }),
        ('Direct Entry & Transfers (200 Level)', {
            'fields': ('accepts_direct_entry', 'de_minimum_qualification', 'accepts_transfers', 'minimum_transfer_cgpa'),
            'classes': ('collapse',)
        }),
        ('Financials & Logistics', {
            'fields': ('total_school_fees', 'acceptance_fee', 'hostel_fees_included', 'allows_installment_payments', 'scholarships_available'),
        }),
        ('Policy & Status', {
            'fields': ('nuc_accreditation_status', 'duration_years', 'admission_deadline', 'is_currently_admitting'),
        }),
    )