import json
import random

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone

from .models import GameFilm, GameResult

MAX_YEAR_DIFF = 10


def hub(request):
    return render(request, 'film_games/hub.html')


# ── Higher or Lower ────────────────────────────────────────────────────────────

def higher_lower(request):
    return render(request, 'film_games/higher_lower.html')


def higher_lower_pair(request):
    """Return two random approved films with different release years."""
    seen = request.session.get('hl_seen', [])

    films = list(
        GameFilm.objects.filter(approved=True)
        .exclude(tmdb_id__in=seen[-30:])
        .values('tmdb_id', 'title', 'release_date', 'poster_path')
    )

    if len(films) < 2:
        films = list(
            GameFilm.objects.filter(approved=True)
            .values('tmdb_id', 'title', 'release_date', 'poster_path')
        )

    if len(films) < 2:
        return JsonResponse({'error': 'Not enough approved films in pool'}, status=400)

    pair = None
    for _ in range(50):
        a, b = random.sample(films, 2)
        diff = abs(a['release_date'].year - b['release_date'].year)
        if 0 < diff <= MAX_YEAR_DIFF:
            pair = (a, b)
            break

    if not pair:
        return JsonResponse({'error': 'Could not find a valid pair'}, status=400)

    a, b = pair

    return JsonResponse({
        'film_a': {
            'tmdb_id': a['tmdb_id'],
            'title': a['title'],
            'poster_path': a['poster_path'],
        },
        'film_b': {
            'tmdb_id': b['tmdb_id'],
            'title': b['title'],
            'poster_path': b['poster_path'],
        },
    })


def higher_lower_answer(request):
    """Validate the user's answer, update session score, save result on game over."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body)
    film_a_id = data.get('film_a_id')
    film_b_id = data.get('film_b_id')
    chosen_id = data.get('chosen_id')

    try:
        film_a = GameFilm.objects.get(tmdb_id=film_a_id)
        film_b = GameFilm.objects.get(tmdb_id=film_b_id)
    except GameFilm.DoesNotExist:
        return JsonResponse({'error': 'Film not found'}, status=404)

    older = film_a if film_a.release_date < film_b.release_date else film_b
    correct = str(chosen_id) == str(older.tmdb_id)

    if correct:
        request.session['hl_score'] = request.session.get('hl_score', 0) + 1
        seen = request.session.get('hl_seen', [])
        seen.extend([film_a_id, film_b_id])
        request.session['hl_seen'] = seen[-60:]
        request.session.modified = True

        return JsonResponse({
            'correct': True,
            'score': request.session['hl_score'],
            'film_a_year': str(film_a.release_date.year),
            'film_b_year': str(film_b.release_date.year),
        })

    else:
        score = request.session.get('hl_score', 0)
        request.session['hl_score'] = 0
        request.session['hl_seen'] = []
        request.session.modified = True

        if request.user.is_authenticated and score > 0:
            result, created = GameResult.objects.get_or_create(
                user=request.user,
                game=GameResult.GAME_HIGHER_LOWER,
                date=timezone.now().date(),
                defaults={'score': score},
            )
            if not created and score > result.score:
                result.score = score
                result.save()

        return JsonResponse({
            'correct': False,
            'score': score,
            'film_a_year': str(film_a.release_date.year),
            'film_b_year': str(film_b.release_date.year),
        })
