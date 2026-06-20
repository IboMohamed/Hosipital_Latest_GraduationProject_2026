from flask import Flask, render_template, request, redirect, session
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "salamtak_secret"


# ================= DATABASE =================
def get_db():
    return pyodbc.connect(
        r"Driver={ODBC Driver 17 for SQL Server};"
        r"Server=DESKTOP-8MI2AQC\SQLEXPRESS;"
        r"Database=Salamtak;"
        r"Trusted_Connection=yes;"
        r"TrustServerCertificate=yes;"
    )


# ================= LOGIN (UPDATED) =================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,))

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[10], password):  
            # user[10] = password column (IMPORTANT: adjust if needed)

            session["user"] = user[1]
            session["role"] = user[11]

            if session["role"] == "admin":
                return redirect("/admin")
            elif session["role"] == "pharmacist":
                return redirect("/pharmacist")
            elif session["role"] == "doctor":
                return redirect("/doctor")
            elif session["role"] == "patient":
                return redirect("/patient")
            else:
                return redirect("/dashboard")
        else:
            error = "Invalid login"

    return render_template("login.html", error=error)


# ================= REGISTER (HASHED) =================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":

        first_name = request.form["first_name"]
        middle_name = request.form["middle_name"]
        last_name = request.form["last_name"]
        address = request.form["address"]
        emergency_contact = request.form["emergency_contact"]
        email = request.form["email"]
        phone = request.form["phone"]
        phone2 = request.form.get("phone2")

        gender = request.form["gender"]
        birth_date = request.form["birth_date"]

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            error = "Passwords do not match"
            return render_template("register.html", error=error)

        hashed_password = generate_password_hash(password)

        role = "patient"
        status = "approved"
        full_name = f"{first_name} {middle_name} {last_name}"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
    INSERT INTO users
    (username, first_name, middle_name, last_name,
     email, phone, phone2, gender, birth_date,
     password, role, status)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    full_name,
    first_name,
    middle_name,
    last_name,
    email,
    phone,
    phone2,
    gender,
    birth_date,
    hashed_password,
    role,
    status
))

        user_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Patients (user_id, address, emergency_contact)
            VALUES (?, ?, ?)
        """, (user_id, address, emergency_contact))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html", error=error)


# ================= ADD USER (ADMIN) =================
@app.route("/add_user", methods=["GET", "POST"])
def add_user():

    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":

        first_name = request.form["first_name"]
        middle_name = request.form["middle_name"]
        last_name = request.form["last_name"]
        phone2 = request.form.get("phone2")
        gender = request.form.get("gender")
        birth_date = request.form.get("birth_date")
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)
        full_name = f"{first_name} {middle_name} {last_name}"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users
            (username, first_name, middle_name, last_name,
             email, phone, password, role, status , phone2, gender, birth_date)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            hashed_password,
            role,
            "approved",
            phone2,
            gender,
            birth_date

        ))

        user_id = cursor.fetchone()[0]
        print("NEW USER ID =", user_id)

        if role == "doctor":
            cursor.execute("""
                INSERT INTO Doctors
                (user_id, specialization, experience_years, clinic_address)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                request.form["specialization"],
                request.form["experience"],
                request.form["address"]
            ))

        elif role == "pharmacist":
            cursor.execute("""
                INSERT INTO Pharmacy
                (user_id, pharmacy_name, location)
                VALUES (?, ?, ?)
            """, (
                user_id,
                request.form["pharmacy_name"],
                request.form["location"]
            ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("add_user.html")


# ================= ADMIN =================
@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # ================= USERS =================
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    # ================= DOCTORS =================
    cursor.execute("SELECT COUNT(*) FROM Doctors")
    doctors_count = cursor.fetchone()[0]

    # ================= APPOINTMENTS =================
    cursor.execute("SELECT COUNT(*) FROM Appointments")
    appointments_count = cursor.fetchone()[0]

    # ================= PHARMACY ITEMS =================
    cursor.execute("SELECT COUNT(*) FROM Medicines")
    medicines_count = cursor.fetchone()[0]

    # ================= USERS LIST =================
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        users_count=users_count,
        doctors_count=doctors_count,
        appointments_count=appointments_count,
        medicines_count=medicines_count
    )

# ================= DASHBOARD ROUTER =================
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin")
    elif role == "doctor":
        return redirect("/doctor")
    elif role == "patient":
        return redirect("/patient")
    elif role == "pharmacist":
        return redirect("/pharmacist")

    return "Unknown role"

# ================= Doctor =================
@app.route("/doctor")
def doctor():

    if session.get("role") != "doctor":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    username = session["user"]

    cursor.execute("""
        SELECT d.doctor_id
        FROM Doctors d
        JOIN users u
            ON d.user_id = u.id
        WHERE u.username = ?
    """, (username,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()
        return "Doctor profile not found"

    doctor_id = doctor[0]

    # Patients count
    cursor.execute("""
        SELECT COUNT(DISTINCT patient_id)
        FROM Appointments
        WHERE doctor_id = ?
    """, (doctor_id,))
    patients_count = cursor.fetchone()[0]

    # Appointments count
    cursor.execute("""
        SELECT COUNT(*)
        FROM Appointments
        WHERE doctor_id = ?
    """, (doctor_id,))
    appointments_count = cursor.fetchone()[0]

    # Prescriptions count
    cursor.execute("""
        SELECT COUNT(*)
        FROM Prescription
        WHERE doctor_id = ?
    """, (doctor_id,))
    prescriptions_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "doctor.html",
        patients_count=patients_count,
        appointments_count=appointments_count,
        prescriptions_count=prescriptions_count
    )

# ================= Doctors =================
@app.route("/doctors")
def doctors():

    if session.get("role") != "admin":
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    if search:

        cursor.execute("""
            SELECT d.doctor_id,
                   u.username,
                   d.specialization,
                   d.experience_years,
                   d.clinic_address
            FROM Doctors d
            JOIN users u ON d.user_id = u.id
            WHERE CAST(d.doctor_id AS VARCHAR(20)) LIKE ?
               OR u.username LIKE ?
               OR d.specialization LIKE ?
               OR CAST(d.experience_years AS VARCHAR(20)) LIKE ?
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT d.doctor_id,
                   u.username,
                   d.specialization,
                   d.experience_years,
                   d.clinic_address
            FROM Doctors d
            JOIN users u ON d.user_id = u.id
        """)

    doctors = cursor.fetchall()

    conn.close()

    return render_template(
        "doctors.html",
        doctors=doctors,
        search=search
    )

# ================= Doctor Patients =================
@app.route("/doctor_patients")
def doctor_patients():

    if session.get("role") != "doctor":
        return redirect("/login")

    username = session["user"]

    conn = get_db()
    cursor = conn.cursor()

    # Get doctor_id
    cursor.execute("""
        SELECT d.doctor_id
        FROM Doctors d
        JOIN users u
            ON d.user_id = u.id
        WHERE u.username = ?
    """, (username,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()
        return "Doctor profile not found"

    doctor_id = doctor[0]

    # Get patients assigned through appointments
    cursor.execute("""
        SELECT DISTINCT
            p.patient_id,
            u.username,
            u.email,
            u.phone

        FROM Appointments a

        JOIN Patients p
            ON a.patient_id = p.patient_id

        JOIN users u
            ON p.user_id = u.id

        WHERE a.doctor_id = ?

        ORDER BY u.username
    """, (doctor_id,))

    patients = cursor.fetchall()

    conn.close()

    return render_template(
        "doctor_patients.html",
        patients=patients
    )

# ================= Doctor Appointments =================
@app.route("/doctor_appointments")
def doctor_appointments():

    if session.get("role") != "doctor":
        return redirect("/login")

    username = session["user"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.doctor_id
        FROM Doctors d
        JOIN users u
            ON d.user_id = u.id
        WHERE u.username = ?
    """, (username,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()
        return "Doctor profile not found"

    doctor_id = doctor[0]

    cursor.execute("""
        SELECT
            a.appointment_id,
            p_user.username,
            d_user.username,
            a.appointment_date

        FROM Appointments a

        JOIN Patients p
            ON a.patient_id = p.patient_id

        JOIN users p_user
            ON p.user_id = p_user.id

        JOIN Doctors d
            ON a.doctor_id = d.doctor_id

        JOIN users d_user
            ON d.user_id = d_user.id

        WHERE a.doctor_id = ?

        ORDER BY a.appointment_date
    """, (doctor_id,))

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "doctor_appointments.html",
        appointments=appointments
    )

# ================= Doctor Prescriptions =================
@app.route("/doctor_prescriptions")
def doctor_prescriptions():

    if session.get("role") != "doctor":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    # Load patients
    cursor.execute("""
       SELECT
    p.patient_id,
    u.username,
    MAX(a.appointment_id) AS appointment_id
FROM Patients p
JOIN users u
    ON p.user_id = u.id
LEFT JOIN Appointments a
    ON p.patient_id = a.patient_id
GROUP BY
    p.patient_id,
    u.username
ORDER BY u.username
    """)

    patients = cursor.fetchall()

    # Load prescriptions
    cursor.execute("""
        SELECT
            pr.prescription_id,
            u.first_name + ' ' + u.last_name,
            pr.issue_date,
            pr.notes
        FROM Prescription pr
        JOIN Patients p
            ON pr.patient_id = p.patient_id
        JOIN users u
            ON p.user_id = u.id
        ORDER BY pr.issue_date DESC
    """)

    prescriptions = cursor.fetchall()

    conn.close()

    return render_template(
        "doctor_prescriptions.html",
        patients=patients,
        prescriptions=prescriptions
    )

# ================= Add Prescription =================
@app.route("/add_prescription", methods=["POST"])
def add_prescription():

    if session.get("role") != "doctor":
        return redirect("/login")

    appointment_id = request.form["appointment_id"]
    notes = request.form["notes"]

    conn = get_db()
    cursor = conn.cursor()

    username = session["user"]

    cursor.execute("""
        SELECT d.doctor_id
        FROM Doctors d
        JOIN users u
            ON d.user_id = u.id
        WHERE u.username = ?
    """, (username,))

    doctor = cursor.fetchone()

    if not doctor:
        conn.close()
        return "Doctor profile not found"

    doctor_id = doctor[0]

    cursor.execute("""
        SELECT patient_id
        FROM Appointments
        WHERE appointment_id = ?
          AND doctor_id = ?
    """, (appointment_id, doctor_id))

    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        return "Appointment not found"

    patient_id = appointment[0]

    cursor.execute("""
        INSERT INTO Prescription
        (
            appointment_id,
            doctor_id,
            patient_id,
            issue_date,
            notes
        )
        VALUES (?, ?, ?, GETDATE(), ?)
    """, (
        appointment_id,
        doctor_id,
        patient_id,
        notes
    ))

    conn.commit()
    conn.close()

    return redirect("/doctor_prescriptions")

# ================= Medical Reports =================
@app.route("/medical_reports")
def medical_reports():

    if session.get("role") != "doctor":
        return redirect("/login")

    return render_template("medical_reports.html")

# ================= Patient =================
@app.route("/patient")
def patient():

    if session.get("role") != "patient":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    username = session["user"]

    cursor.execute("""
        SELECT p.patient_id
        FROM Patients p
        JOIN users u
            ON p.user_id = u.id
        WHERE u.username = ?
    """, (username,))

    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return "Patient profile not found"

    patient_id = patient[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Appointments
        WHERE patient_id = ?
    """, (patient_id,))
    appointments_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Prescription
        WHERE patient_id = ?
    """, (patient_id,))
    prescriptions_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "patient.html",
        appointments_count=appointments_count,
        prescriptions_count=prescriptions_count
    )

# ================= Pharmacist =================
@app.route("/pharmacist")
def pharmacist():

    if session.get("role") != "pharmacist":
        return redirect("/login")

    return render_template("pharmacist.html")

# ================= Departments =================
@app.route("/departments", methods=["GET", "POST"])
def departments():

    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "")

    if search:

        cursor.execute("""
            SELECT *
            FROM Departments
            WHERE CAST(department_id AS VARCHAR) LIKE ?
               OR name LIKE ?
               OR description LIKE ?
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

    else:
        cursor.execute("SELECT * FROM Departments")

    data = cursor.fetchall()

    conn.close()

    return render_template(
        "departments.html",
        departments=data,
        search=search
    )

# ================= Delete Department =================
@app.route("/delete_department/<int:id>")
def delete_department(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Departments
        WHERE department_id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/departments")

# ================= Appointments =================
@app.route("/appointments")
def appointments():

    if session.get("role") != "admin":
        return redirect("/login")

    search = request.args.get("search", "")

    conn = get_db()
    cursor = conn.cursor()

    if search:

        cursor.execute("""
            SELECT
                a.appointment_id,

                p_user.first_name + ' ' + p_user.last_name AS patient_name,

                d_user.first_name + ' ' + d_user.last_name AS doctor_name,

                a.appointment_date,
                a.status

            FROM Appointments a

            JOIN Patients p
                ON a.patient_id = p.patient_id

            JOIN users p_user
                ON p.user_id = p_user.id

            JOIN Doctors d
                ON a.doctor_id = d.doctor_id

            JOIN users d_user
                ON d.user_id = d_user.id

            WHERE
                CAST(a.appointment_id AS VARCHAR(20)) LIKE ?
                OR p_user.first_name LIKE ?
                OR p_user.last_name LIKE ?
                OR d_user.first_name LIKE ?
                OR d_user.last_name LIKE ?
                OR a.status LIKE ?
        """,
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%")

    else:

        cursor.execute("""
            SELECT
                a.appointment_id,
                p_user.username as PatientName,
                d_user.username as DoctorName,
                a.appointment_date,
                a.status

            FROM Appointments a

            JOIN Patients p
                ON a.patient_id = p.patient_id

            JOIN users p_user
                ON p.user_id = p_user.id

            JOIN Doctors d
                ON a.doctor_id = d.doctor_id

            JOIN users d_user
                ON d.user_id = d_user.id
        """)

    appointments = cursor.fetchall()

    conn.close()

    return render_template(
        "appointments.html",
        appointments=appointments,
        search=search
    )

# ================= Patient Appointments =================
@app.route("/patient_appointments")
def patient_appointments():

    if session.get("role") != "patient":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    username = session["user"]

    cursor.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, (username,))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT patient_id
        FROM Patients
        WHERE user_id = ?
    """, (user[0],))

    patient = cursor.fetchone()

    patient_id = patient[0]

    # appointments
    cursor.execute("""
        SELECT
            a.appointment_id,
            u.username,
            a.appointment_date
        FROM Appointments a
        JOIN Doctors d
            ON a.doctor_id = d.doctor_id
        JOIN users u
            ON d.user_id = u.id
        WHERE a.patient_id = ?
    """, (patient_id,))

    appointments = cursor.fetchall()

    # doctors list
    cursor.execute("""
        SELECT
            d.doctor_id,
            u.username,
            d.specialization
        FROM Doctors d
        JOIN users u
            ON d.user_id = u.id
    """)

    doctors = cursor.fetchall()

    conn.close()

    return render_template(
        "patient_appointments.html",
        appointments=appointments,
        doctors=doctors
    )

# ================= Book Appointment =================
@app.route("/book_appointment", methods=["POST"])
def book_appointment():

    if session.get("role") != "patient":
        return redirect("/login")

    doctor_id = request.form["doctor_id"]
    appointment_date = request.form["appointment_date"]

    appointment_date = datetime.strptime(
        appointment_date,
        "%Y-%m-%dT%H:%M"
    )

    appointment_date = appointment_date.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = get_db()
    cursor = conn.cursor()

    username = session["user"]

    cursor.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, (username,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT patient_id
        FROM Patients
        WHERE user_id = ?
    """, (user[0],))
    patient = cursor.fetchone()

    patient_id = patient[0]

    # Check if doctor already has appointment at same time
    cursor.execute("""
        SELECT appointment_id
        FROM Appointments
        WHERE doctor_id = ?
          AND appointment_date = ?
    """, (doctor_id, appointment_date))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return "This time slot is already booked."

    # Insert appointment
    cursor.execute("""
        INSERT INTO Appointments
        (
            patient_id,
            doctor_id,
            appointment_date,
            status,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        patient_id,
        doctor_id,
        appointment_date,
        "Completed",
        ""
    ))

    conn.commit()
    conn.close()

    return redirect("/patient_appointments")

# ================= Patient Prescriptions =================
@app.route("/patient_prescriptions")
def patient_prescriptions():

    if session.get("role") != "patient":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient_id
        FROM Patients p
        JOIN users u
            ON p.user_id = u.id
        WHERE u.username = ?
    """, (session["user"],))

    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return "Patient profile not found"

    patient_id = patient[0]

    cursor.execute("""
    SELECT
        p.prescription_id,
        d_user.username AS doctor_name,
        p.issue_date,
        p.notes
    FROM Prescription p

    JOIN Doctors d
        ON p.doctor_id = d.doctor_id

    JOIN users d_user
        ON d.user_id = d_user.id

    WHERE p.patient_id = ?

    ORDER BY p.issue_date DESC
""", (patient_id,))

    prescriptions = cursor.fetchall()

    conn.close()

    return render_template(
        "patient_prescriptions.html",
        prescriptions=prescriptions
    )

# ================= Patient Reports =================
@app.route("/patient_reports")
def patient_reports():

    if session.get("role") != "patient":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT patient_id
        FROM Patients p
        JOIN users u
            ON p.user_id = u.id
        WHERE u.username = ?
    """, (session["user"],))

    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return "Patient profile not found"

    patient_id = patient[0]

    cursor.execute("""
        SELECT *
        FROM MedicalReports
        WHERE patient_id = ?
    """, (patient_id,))

    reports = cursor.fetchall()

    conn.close()

    return render_template(
        "patient_reports.html",
        reports=reports
    )

# ================= ADD DEPARTMENT =================
@app.route("/add_department", methods=["GET", "POST"])
def add_department():

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Departments(name, description)
            VALUES (?, ?)
        """, (name, description))

        conn.commit()
        conn.close()

        return redirect("/departments")

    return render_template("add_department.html")


# ================= Profile =================
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            username,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            role,
            status
        FROM users
        WHERE username = ?
    """, (session["user"],))

    user = cursor.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )

# ================= Pharmacy Stock =================
@app.route("/medicines_stock")
@app.route("/pharmacy_stock")
def medicines_stock():

    if session.get("role") not in ("pharmacist", "admin"):
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Medicines")
    meds = cursor.fetchall()

    conn.close()

    return render_template(
    "pharmacy_stock.html",
    meds=meds,
    role=session.get("role")
)

# ================= Pharmacy Prescriptions =================
@app.route("/pharmacy_prescriptions")
@app.route("/pharmacy_prescriptions")
def pharmacy_prescriptions():

    if session.get("role") not in ["pharmacist", "admin"]:
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    if search:

        cursor.execute("""
            SELECT
                p.prescription_id,
                du.username AS doctor_name,
                pu.username AS patient_name,
                p.issue_date

            FROM Prescription p

            JOIN Doctors d
                ON p.doctor_id = d.doctor_id

            JOIN users du
                ON d.user_id = du.id

            JOIN Patients pa
                ON p.patient_id = pa.patient_id

            JOIN users pu
                ON pa.user_id = pu.id

            WHERE
                CAST(p.prescription_id AS VARCHAR(20)) LIKE ?
                OR du.username LIKE ?
                OR pu.username LIKE ?
                OR CONVERT(VARCHAR(20), p.issue_date, 120) LIKE ?

            ORDER BY p.issue_date DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT
                p.prescription_id,
                du.username AS doctor_name,
                pu.username AS patient_name,
                p.issue_date

            FROM Prescription p

            JOIN Doctors d
                ON p.doctor_id = d.doctor_id

            JOIN users du
                ON d.user_id = du.id

            JOIN Patients pa
                ON p.patient_id = pa.patient_id

            JOIN users pu
                ON pa.user_id = pu.id

            ORDER BY p.issue_date DESC
        """)

    prescriptions = cursor.fetchall()

    conn.close()

    return render_template(
        "pharmacy_prescriptions.html",
        prescriptions=prescriptions,
        search=search
    )

# ================= Add Medicine =================
@app.route("/add_medicine", methods=["GET", "POST"])
def add_medicine():

    if session.get("role") not in ["admin", "pharmacist"]:
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        stock_quantity = request.form["stock_quantity"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Medicines
            (name, description, price, stock_quantity)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            description,
            price,
            stock_quantity
        ))

        conn.commit()
        conn.close()

        return redirect("/medicines_stock")

    return render_template("add_medicine.html")

# ================= Delete Medicine =================
@app.route("/delete_medicine/<int:id>")
def delete_medicine(id):

    if session.get("role") not in ["admin", "pharmacist"]:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Medicines
        WHERE medicine_id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/pharmacy_stock")

# ================= Update Medicine =================
@app.route("/update_medicine/<int:id>", methods=["GET", "POST"])
def update_medicine(id):

    if session.get("role") not in ["admin", "pharmacist"]:
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT medicine_id, name, description, price, stock_quantity
        FROM Medicines
        WHERE medicine_id = ?
    """, (id,))

    medicine = cursor.fetchone()

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        stock_quantity = request.form["stock_quantity"]

        cursor.execute("""
            UPDATE Medicines
            SET name = ?,
                description = ?,
                price = ?,
                stock_quantity = ?
            WHERE medicine_id = ?
        """, (
            name,
            description,
            price,
            stock_quantity,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/medicines_stock")

    conn.close()

    return render_template(
        "update_medicine.html",
        medicine=medicine
    )

# ================= Prescriptions =================
@app.route("/prescriptions")
def prescriptions():

    search = request.args.get("search", "").strip()
    print("Search =", search)
    conn = get_db()
    cursor = conn.cursor()

    if search:

        cursor.execute("""
    SELECT
        p.prescription_id,
        du.username,
        pu.username,
        p.issue_date

    FROM Prescription p

    JOIN Doctors d
        ON p.doctor_id = d.doctor_id

    JOIN users du
        ON d.user_id = du.id

    JOIN Patients pa
        ON p.patient_id = pa.patient_id

    JOIN users pu
        ON pa.user_id = pu.id

    WHERE
        CAST(p.prescription_id AS VARCHAR(20)) LIKE ?
        OR du.username LIKE ?
        OR pu.username LIKE ?
        OR CONVERT(VARCHAR(10), p.issue_date, 120) LIKE ?
""", (
    f"%{search}%",
    f"%{search}%",
    f"%{search}%",
    f"%{search}%"
))

    else:

        cursor.execute("""
            SELECT
                p.prescription_id,
                du.username,
                pu.username,
                p.issue_date

            FROM Prescription p

            JOIN Doctors d
                ON p.doctor_id = d.doctor_id

            JOIN users du
                ON d.user_id = du.id

            JOIN Patients pa
                ON p.patient_id = pa.patient_id

            JOIN users pu
                ON pa.user_id = pu.id
        """)

    data = cursor.fetchall()
    for row in data:
        print(row)
    conn.close()

    return render_template(
        "prescriptions.html",
        prescriptions=data,
        search=search
    )

# ================= Update Doctors =================
@app.route("/update_doctor/<int:id>", methods=["GET", "POST"])
def update_doctor(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT doctor_id, user_id, specialization,
               experience_years, clinic_address
        FROM Doctors
        WHERE doctor_id=?
    """, (id,))

    doctor = cursor.fetchone()

    if request.method == "POST":

        specialization = request.form["specialization"]
        experience = request.form["experience"]
        address = request.form["address"]

        cursor.execute("""
            UPDATE Doctors
            SET specialization=?, experience_years=?, clinic_address=?
            WHERE doctor_id=?
        """, (specialization, experience, address, id))

        conn.commit()
        conn.close()

        return redirect("/doctors")

    conn.close()

    return render_template("update_doctor.html", doctor=doctor)

# ================= Delete Doctor =================
@app.route("/delete_doctor/<int:id>")
def delete_doctor(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM Doctors
        WHERE doctor_id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/doctors")

# ================= Update Departments =================
@app.route("/update_department/<int:id>", methods=["GET", "POST"])
def update_department(id):

    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department_id, name, description
        FROM Departments
        WHERE department_id = ?
    """, (id,))

    department = cursor.fetchone()

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]

        cursor.execute("""
            UPDATE Departments
            SET name = ?, description = ?
            WHERE department_id = ?
        """, (name, description, id))

        conn.commit()
        conn.close()

        return redirect("/departments")

    conn.close()

    return render_template("update_department.html", department=department)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)