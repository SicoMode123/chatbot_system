from django.db import models

# ==========================================
# 1. THE PARENT: FACULTY
# ==========================================
class Faculty(models.Model):
    name = models.CharField(max_length=200, help_text="e.g., Faculty of Computing")
    dean = models.CharField(max_length=200, help_text="Name of the Dean of the Faculty")
    about = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Faculties"

# ==========================================
# 2. THE CHILD: DEPARTMENT
# ==========================================
class Department(models.Model):
    name = models.CharField(max_length=200, help_text="e.g., Cyber Security")
    head_of_department = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    about = models.TextField()
    contact_email = models.EmailField()

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

# ==========================================
# 3. THE GRANDCHILD: LEVEL INFO (The Boss Move)
# ==========================================
class LevelInfo(models.Model):
    LEVEL_CHOICES = [
        (100, '100 Level'),
        (200, '200 Level'),
        (300, '300 Level'),
        (400, '400 Level'),
        (500, '500 Level'),
    ]
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='levels')
    level = models.IntegerField(choices=LEVEL_CHOICES)
    course_advisor = models.CharField(max_length=200, help_text="Name of the lecturer advising this level")
    course_rep_name = models.CharField(max_length=200, blank=True, null=True)
    special_status = models.CharField(max_length=200, default="In Session", help_text="e.g., In Session, On SIWES, Graduated")

    class Meta:
        # This ensures you can't accidentally create two "100 Level" entries for the same department
        unique_together = ('department', 'level')

    def __str__(self):
        return f"{self.level}L - {self.department.name}"

# ==========================================
# 4. THE GREAT-GRANDCHILD: COURSE
# ==========================================
class Course(models.Model):
    SEMESTER_CHOICES = [
        ('1st', 'First Semester'),
        ('2nd', 'Second Semester'),
    ]

    level_info = models.ForeignKey(LevelInfo, on_delete=models.CASCADE, related_name='courses')
    course_code = models.CharField(max_length=10, help_text="e.g., CYB303")
    title = models.CharField(max_length=200, help_text="e.g., Information Security Risk Management")
    
    # 👉 THE NEW BOSS FIELD 
    semester = models.CharField(max_length=3, choices=SEMESTER_CHOICES, default='1st')
    
    credit_units = models.IntegerField(default=3)
    is_compulsory = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.course_code} - {self.title} ({self.get_semester_display()})"

# ==========================================
# 5. THE PROFILE: ADMISSION REQUIREMENTS
# ==========================================
class AdmissionRequirement(models.Model):
    # 👉 THE LINK TO DEPARTMENT: One Department has ONE Admission Profile
    department = models.OneToOneField(Department, on_delete=models.CASCADE, related_name='admission_info')

    # 1. THE PROSPECTIVE UTME STUDENT ("Will I get in?")
    jamb_cutoff_mark = models.IntegerField(default=150)
    jamb_subject_combination = models.CharField(
        max_length=255, 
        help_text="e.g., Use of English, Math, Physics, and Chemistry",
        default="Use of English and three other relevant subjects."
    )
    compulsory_olevel_subjects = models.TextField(
        help_text="e.g., 5 Credits including English and Math."
    )
    accepts_two_sittings = models.BooleanField(
        default=True, 
        help_text="Check if a student can combine WAEC and NECO."
    )
    requires_math_credit = models.BooleanField(
        default=True, 
        help_text="Does this specific course absolutely require a Math credit?"
    )
    post_utme_screening = models.BooleanField(
        default=False, 
        help_text="True if there is an exam. False if it's just physical document screening."
    )
    requires_first_choice = models.BooleanField(
        default=True, 
        help_text="Must BIU be their 1st choice on the JAMB portal?"
    )

    # 2. THE DIRECT ENTRY & TRANSFER STUDENT ("Alternative Route")
    accepts_direct_entry = models.BooleanField(default=True)
    de_minimum_qualification = models.CharField(
        max_length=200, 
        default="Minimum of Lower Credit in OND, or valid JUPEB/IJMB.",
        help_text="Specify if they need Upper Credit, or if JUPEB is accepted."
    )
    accepts_transfers = models.BooleanField(
        default=True, 
        help_text="Can a 200L student from another university transfer here?"
    )
    minimum_transfer_cgpa = models.CharField(
        max_length=100, 
        blank=True, null=True, 
        help_text="e.g., Minimum CGPA of 2.5 on a 5.0 scale."
    )

    # 3. THE PARENTS & SPONSORS ("Money & Logistics")
    total_school_fees = models.CharField(
        max_length=100, 
        help_text="e.g., ₦850,000 per session"
    )
    acceptance_fee = models.CharField(
        max_length=100, 
        default="₦50,000 (Non-refundable)"
    )
    hostel_fees_included = models.BooleanField(
        default=False, 
        help_text="Are hostel accommodations part of the total_school_fees?"
    )
    allows_installment_payments = models.BooleanField(
        default=True, 
        help_text="Can parents pay per semester?"
    )
    scholarships_available = models.BooleanField(
        default=True, 
        help_text="Are there sibling discounts or bishopric scholarships?"
    )
    admission_deadline = models.CharField(
        max_length=100, 
        blank=True, null=True, 
        help_text="e.g., October 31st, 2026"
    )

    # 4. STAFF & GENERAL PUBLIC ("Policy & Status")
    nuc_accreditation_status = models.CharField(
        max_length=100, 
        default="Fully Accredited",
        help_text="e.g., Fully Accredited, Interim, or Pending."
    )
    duration_years = models.IntegerField(
        default=4, 
        help_text="How many years does this course take? (e.g., 4, 5, 6)"
    )
    is_currently_admitting = models.BooleanField(
        default=True, 
        help_text="Uncheck if the department has reached its quota for the year."
    )

    def __str__(self):
        return f"Full Admission Profile for {self.department.name}"