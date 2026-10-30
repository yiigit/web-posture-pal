from posturepal.movement.domain.models import Exercise

class CatalogRepository:
    def all(self) -> list[Exercise]:
        return [
            Exercise("neck-release", "Neck release", "Neck", 60, "A little space for your neck. A fresh start for your focus.", ("Sit comfortably with your shoulders relaxed.", "Gently tilt your right ear toward your right shoulder. Hold comfortably.", "Return to center and repeat on the left. Keep breathing naturally."), "Seated", "neck"),
            Exercise("shoulder-rolls", "Shoulder rolls", "Shoulders", 60, "Let go of the tension you didn't know you were holding.", ("Sit or stand with your arms relaxed.", "Slowly lift your shoulders, roll them back, and lower them.", "Repeat gently, then reverse direction."), "Seated or standing", "shoulders"),
            Exercise("seated-twist", "Seated spinal twist", "Back", 90, "Give your back a gentle change of direction.", ("Sit tall with both feet flat on the floor.", "Turn your upper body gently to the right, keeping your hips forward.", "Return to center and repeat to the left. Do not force the turn."), "Seated", "twist"),
            Exercise("chest-opener", "Chest opener", "Shoulders", 60, "Open up after a long stretch at your desk.", ("Stand or sit tall with your arms by your sides.", "Gently draw your shoulder blades together and open your palms forward.", "Hold briefly, release, and repeat without arching your lower back."), "Seated or standing", "chest"),
            Exercise("wrist-reset", "Wrist & finger reset", "Wrists", 45, "A well-earned breather for your busiest hands.", ("Rest your forearms comfortably and relax your hands.", "Slowly open and close your fingers.", "Make small, comfortable wrist circles in both directions."), "Seated", "wrists"),
            Exercise("standing-reach", "Standing sky reach", "Full body", 60, "Step away from your chair and find a little length.", ("Stand with your feet comfortably apart.", "Reach both arms overhead as far as feels comfortable.", "Lower your arms slowly and repeat, breathing steadily."), "Standing", "reach"),
            Exercise("ankle-circles", "Ankle circles", "Legs", 60, "Bring a little movement to your lower half.", ("Sit upright with your feet on the floor.", "Lift one foot slightly and circle your ankle slowly in each direction.", "Lower your foot and repeat on the other side."), "Seated", "legs"),
            Exercise("walking-break", "Mindful walking break", "Full body", 180, "Leave your desk behind. Come back a little clearer.", ("Stand up slowly and choose a clear walking route.", "Walk at an easy pace and relax your shoulders.", "Notice your surroundings and breathe naturally before returning."), "Standing", "walk"),
        ]
