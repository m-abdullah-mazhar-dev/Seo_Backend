from django.db import models

# Create your models here.

class JobOnboardingForm(models.Model):
    # -------------------- Basic Company Details --------------------
    company_name = models.CharField(max_length=255)
    company_website = models.URLField(blank=True, null=True)
    company_address = models.TextField()
    drivers_weekly_earning = models.CharField(max_length=100)
    drivers_weekly_miles = models.CharField(max_length=100)
    cpm = models.CharField(max_length=100)
    driver_percentage = models.CharField(max_length=100, help_text="If applicable")
    truck_make_year = models.CharField(max_length=255)
    hauling_equipment = models.TextField()

    # -------------------- Vehicle Details --------------------
    transmission_automatic = models.BooleanField(default=False)
    transmission_manual = models.BooleanField(default=False)

    position_1099 = models.BooleanField(default=False)
    position_w2 = models.BooleanField(default=False)

    primary_running_areas = models.TextField()
    dedicated_lanes = models.TextField(blank=True, null=True)

    offer_cash_advances = models.BooleanField(default=False)
    cash_advance_amount = models.CharField(max_length=100, blank=True, null=True)

    referral_bonus = models.BooleanField(default=False)
    referral_bonus_amount = models.CharField(max_length=100, blank=True, null=True)

    fuel_card = models.BooleanField(default=False)
    fuel_card_type = models.CharField(max_length=255, blank=True, null=True)

    detention_layover_pay = models.CharField(max_length=100, blank=True, null=True)
    allow_pets_pessenger = models.BooleanField(default=False)

    # -------------------- Driver Benefits --------------------
    benefit_weekly_deposits = models.BooleanField(default=False)
    benefit_all_miles_paid = models.BooleanField(default=False)
    benefit_eco_bonus = models.BooleanField(default=False)
    benefit_pet_policy = models.BooleanField(default=False)
    benefit_rider_policy = models.BooleanField(default=False)
    benefit_gated_parking = models.BooleanField(default=False)
    benefit_eld_compliant = models.BooleanField(default=False)
    benefit_eld_support = models.BooleanField(default=False)
    benefit_dispatch_support = models.BooleanField(default=False)

    truck_governed_speed = models.CharField(max_length=100, blank=True, null=True)
    toll_passes = models.CharField(max_length=255, blank=True, null=True)

    # -------------------- Truck Equipment --------------------
    equip_fridge = models.BooleanField(default=False)
    equip_inverter = models.BooleanField(default=False)
    equip_microwave = models.BooleanField(default=False)
    equip_led = models.BooleanField(default=False)
    equip_apu = models.BooleanField(default=False)
    equip_disc_brakes = models.BooleanField(default=False)
    equip_no_inward_cam = models.BooleanField(default=False)
    equip_partial_equipment = models.BooleanField(default=False)

    # -------------------- Company Logo & Info --------------------
    company_logo = models.FileField(upload_to="logos/", blank=True, null=True)
    mc_dot_number = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=50)
    hiring_email = models.EmailField()

    terminal = models.CharField(max_length=255)
    governed_speed_detail = models.CharField(max_length=255)
    truck_make_year = models.CharField(max_length=255)

    # -------------------- CDL Requirements --------------------
    CDL_EXPERIENCE_CHOICES = [
        ("3", "3 Months"),
        ("6", "6 Months"),
        ("12", "1 Year"),
        ("18", "1.5 Years"),
        ("24", "2 Years"),
        ("36", "3+ Years"),
    ]
    cdl_experience_required = models.CharField(max_length=10, choices=CDL_EXPERIENCE_CHOICES)

    HIRING_AGE_CHOICES = [
        ("21", "21"),
        ("23", "23"),
        ("custom", "Custom"),
    ]
    minimum_hiring_age = models.CharField(max_length=20, choices=HIRING_AGE_CHOICES)
    hiring_age_custom = models.CharField(max_length=100, blank=True, null=True)

    disqualify_sap_dui_dwi = models.BooleanField(default=False)
    clean_clearinghouse = models.CharField(max_length=255)
    clean_drug_test = models.CharField(max_length=255)

    # -------------------- Driver Benefits Main --------------------
    main_weekly_deposits = models.BooleanField(default=False)
    main_safety_bonus = models.BooleanField(default=False)
    main_referral_bonus = models.BooleanField(default=False)
    main_dispatch_support = models.BooleanField(default=False)

    # -------------------- Equipment Main --------------------
    main_auto_transmission = models.BooleanField(default=False)
    main_manual_transmission = models.BooleanField(default=False)
    main_equip_fridge = models.BooleanField(default=False)
    main_equip_inverter = models.BooleanField(default=False)
    main_equip_microwave = models.BooleanField(default=False)
    main_equip_led = models.BooleanField(default=False)

    # -------------------- Travel Main --------------------
    travel_provided = models.BooleanField(default=False)
    travel_description = models.TextField(blank=True, null=True)

    # -------------------- Extras Main --------------------
    escrow_required = models.BooleanField(default=False)
    escrow_description = models.TextField(blank=True, null=True)

    repair_shop_onsite = models.BooleanField(default=False)
    gated_vehicle_parking = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name
