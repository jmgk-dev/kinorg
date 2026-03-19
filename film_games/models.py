from django.db import models
from django.conf import settings


class GameFilm(models.Model):
    """Pool of approved films used across all games."""

    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=200)
    release_date = models.DateField()
    poster_path = models.CharField(max_length=200, blank=True)
    vote_count = models.IntegerField(default=0)
    approved = models.BooleanField(default=False)
    used_framed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-vote_count']

    def __str__(self):
        return f"{self.title} ({self.release_date.year})"


class DailyFramed(models.Model):
    """One film per day for the Framed game."""

    date = models.DateField(unique=True)
    film = models.ForeignKey(GameFilm, on_delete=models.PROTECT)

    def __str__(self):
        return f"Framed {self.date} — {self.film.title}"


class GameResult(models.Model):

    GAME_FRAMED = 'framed'
    GAME_HIGHER_LOWER = 'higher_lower'

    GAME_CHOICES = [
        (GAME_FRAMED, 'Framed'),
        (GAME_HIGHER_LOWER, 'Higher or Lower'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='game_results',
    )
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    date = models.DateField()
    # Framed: attempts used (1-6), 7 = failed
    # Higher or Lower: streak length
    score = models.IntegerField()

    class Meta:
        unique_together = [('user', 'game', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f"{self.user} — {self.game} — {self.date} — {self.score}"
