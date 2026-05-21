"""
Script de seed para criar dados de teste do MEDARA.
Rode com: python seed.py
"""
import asyncio
import sys
from app.database import engine, AsyncSessionLocal
from app.models.base import Base
from app.models.user import User, UserRole, RefreshToken
from app.models.company import Company, CompanyPlan
from app.models.doctor import Doctor, Specialty, DoctorSpecialty
from app.models.consultation import Consultation
from app.core.security import hash_password
from sqlalchemy import select, delete


async def seed():
    # Garante que as tabelas existem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Limpa dados anteriores (dev only)
        await db.execute(delete(DoctorSpecialty))
        await db.execute(delete(Doctor))
        await db.execute(delete(Specialty))
        await db.execute(delete(RefreshToken))
        await db.execute(delete(User))
        await db.execute(delete(Company))
        await db.commit()

        print("[SEED] Criando dados de seed do MEDARA...")

        # ── Empresa ──────────────────────────────────────────
        company = Company(
            name="TechCorp Ltda",
            domain="techcorp.com.br",
            plan=CompanyPlan.gold,
            is_active=True,
        )
        db.add(company)
        await db.flush()
        print(f"  [OK]Empresa: {company.name} (ID: {company.id})")

        # ── Admin da plataforma ───────────────────────────────
        admin = User(
            email="admin@medara.com.br",
            hashed_password=hash_password("Admin@123"),
            full_name="Admin MEDARA",
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
        )
        admin.avatar_initials = admin.computed_initials
        db.add(admin)

        # ── Gestor/RH ─────────────────────────────────────────
        manager = User(
            email="rh@techcorp.com.br",
            hashed_password=hash_password("Gestor@123"),
            full_name="Carlos Mendes",
            role=UserRole.manager,
            company_id=company.id,
            is_active=True,
            is_verified=True,
        )
        manager.avatar_initials = manager.computed_initials
        db.add(manager)

        # ── Funcionários ──────────────────────────────────────
        employees_data = [
            ("Maria Silva", "maria@techcorp.com.br"),
            ("João Santos", "joao@techcorp.com.br"),
            ("Ana Lima", "ana@techcorp.com.br"),
        ]
        for full_name, email in employees_data:
            u = User(
                email=email,
                hashed_password=hash_password("Func@123"),
                full_name=full_name,
                role=UserRole.employee,
                company_id=company.id,
                is_active=True,
                is_verified=True,
            )
            u.avatar_initials = u.computed_initials
            db.add(u)

        await db.flush()
        print(f"  [OK]Admin: admin@medara.com.br / Admin@123")
        print(f"  [OK]Gestor: rh@techcorp.com.br / Gestor@123")
        print(f"  [OK]Funcionários: maria/joao/ana @techcorp.com.br / Func@123")

        # ── Especialidades ────────────────────────────────────
        specialty_names = [
            "Clínico Geral", "Psicólogo", "Nutricionista",
            "Cardiologista", "Dermatologista", "Ginecologista",
        ]
        specialties = {}
        for name in specialty_names:
            s = Specialty(name=name)
            db.add(s)
            await db.flush()
            specialties[name] = s
        print(f"  [OK]{len(specialties)} especialidades criadas")

        # ── Médicos ───────────────────────────────────────────
        doctors_data = [
            ("Dr. Rafael Souza",    "dr.rafael@medara.com.br",  "123456", "SP", "Clínico Geral com 10 anos de experiência.",    ["Clínico Geral"],  4.9, 312, True),
            ("Dra. Ana Lima",       "dra.ana@medara.com.br",    "234567", "RJ", "Psicóloga especialista em saúde corporativa.", ["Psicólogo"],      4.8, 256, True),
            ("Dra. Carla Matos",    "dra.carla@medara.com.br",  "345678", "SP", "Nutricionista funcional e esportiva.",         ["Nutricionista"], 4.7, 189, True),
            ("Dr. Marcos Vieira",   "dr.marcos@medara.com.br",  "456789", "MG", "Cardiologista com foco em prevenção.",         ["Cardiologista"], 4.9, 401, True),
            ("Dra. Camila Ferreira","dra.camila@medara.com.br", "567890", "SP", "Dermatologista clínica e estética.",           ["Dermatologista"],4.8, 198, False),
            ("Dra. Luciana Prado",  "dra.luciana@medara.com.br","678901", "RJ", "Ginecologista e obstetra.",                    ["Ginecologista"], 4.9, 312, False),
        ]
        for full_name, email, crm, state, bio, specs, rating, reviews, available in doctors_data:
            doc_user = User(
                email=email,
                hashed_password=hash_password("Doctor@123"),
                full_name=full_name,
                role=UserRole.doctor,
                is_active=True,
                is_verified=True,
            )
            doc_user.avatar_initials = doc_user.computed_initials
            db.add(doc_user)
            await db.flush()

            doctor = Doctor(
                user_id=doc_user.id,
                crm=crm,
                crm_state=state,
                bio=bio,
                is_available=available,
                rating_avg=rating,
                rating_count=reviews,
            )
            db.add(doctor)
            await db.flush()

            for spec_name in specs:
                db.add(DoctorSpecialty(
                    doctor_id=doctor.id,
                    specialty_id=specialties[spec_name].id,
                ))

        await db.commit()
        print(f"  [OK]{len(doctors_data)} médicos criados (senha: Doctor@123)")

        print("\n[DONE] Seed concluido!\n")
        print("  Acesse http://localhost:8000/docs para explorar a API.")
        print("\n  Credenciais de teste:")
        print("  ┌─────────────────────────────────────┬──────────────┐")
        print("  │ E-mail                              │ Senha        │")
        print("  ├─────────────────────────────────────┼──────────────┤")
        print("  │ admin@medara.com.br                 │ Admin@123    │")
        print("  │ rh@techcorp.com.br                  │ Gestor@123   │")
        print("  │ maria@techcorp.com.br               │ Func@123     │")
        print("  │ dr.rafael@medara.com.br             │ Doctor@123   │")
        print("  └─────────────────────────────────────┴──────────────┘")


if __name__ == "__main__":
    asyncio.run(seed())
