import json
import random

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone

from .models import GameFilm, DailyFramed, GameResult


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


# ── Framed ─────────────────────────────────────────────────────────────────────

MAX_YEAR_DIFF = 10

BLUR_LEVELS = [
    'blur(30px)',
    'blur(20px)',
    'blur(12px)',
    'blur(6px)',
    'blur(2px)',
    'blur(0px)',
]

MAX_ATTEMPTS = 6


def _get_or_create_daily_framed():
    today = timezone.now().date()
    try:
        return DailyFramed.objects.get(date=today)
    except DailyFramed.DoesNotExist:
        used_ids = DailyFramed.objects.values_list('film_id', flat=True)
        candidates = list(GameFilm.objects.filter(approved=True).exclude(id__in=used_ids))
        if not candidates:
            candidates = list(GameFilm.objects.filter(approved=True))
        if not candidates:
            return None
        film = random.choice(candidates)
        return DailyFramed.objects.create(date=today, film=film)


def _get_framed_session(request, today):
    if request.session.get('framed_date') != str(today):
        request.session['framed_date'] = str(today)
        request.session['framed_guesses'] = []
        request.session['framed_solved'] = False
        request.session.modified = True
    return {
        'guesses': request.session.get('framed_guesses', []),
        'solved': request.session.get('framed_solved', False),
    }


def framed(request):
    today = timezone.now().date()
    daily = _get_or_create_daily_framed()

    if not daily:
        return render(request, 'film_games/framed.html', {'no_film': True})

    state = _get_framed_session(request, today)
    guesses = state['guesses']
    solved = state['solved']
    game_over = solved or len(guesses) >= MAX_ATTEMPTS
    blur_index = min(len(guesses), MAX_ATTEMPTS - 1)

    context = {
        'daily': daily,
        'guesses': guesses,
        'solved': solved,
        'game_over': game_over,
        'attempts': len(guesses),
        'max_attempts': MAX_ATTEMPTS,
        'blur_filter': BLUR_LEVELS[blur_index],
    }
    return render(request, 'film_games/framed.html', context)


def framed_guess(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    today = timezone.now().date()
    daily = _get_or_create_daily_framed()
    if not daily:
        return JsonResponse({'error': 'No film for today'}, status=400)

    state = _get_framed_session(request, today)
    guesses = state['guesses']

    if state['solved'] or len(guesses) >= MAX_ATTEMPTS:
        return JsonResponse({'error': 'Game already over'}, status=400)

    data = json.loads(request.body)
    skip = data.get('skip', False)

    if skip:
        guesses.append({'skip': True, 'correct': False, 'title': 'Skipped'})
    else:
        tmdb_id = data.get('tmdb_id')
        try:
            guessed_film = GameFilm.objects.get(tmdb_id=tmdb_id)
        except GameFilm.DoesNotExist:
            return JsonResponse({'error': 'Film not found'}, status=404)

        correct = guessed_film.tmdb_id == daily.film.tmdb_id
        guesses.append({
            'skip': False,
            'correct': correct,
            'title': guessed_film.title,
            'tmdb_id': guessed_film.tmdb_id,
        })

        if correct:
            request.session['framed_solved'] = True

    request.session['framed_guesses'] = guesses
    request.session.modified = True

    solved = request.session.get('framed_solved', False)
    game_over = solved or len(guesses) >= MAX_ATTEMPTS
    blur_index = min(len(guesses), MAX_ATTEMPTS - 1)

    if game_over and request.user.is_authenticated:
        score = len(guesses) if solved else MAX_ATTEMPTS + 1
        GameResult.objects.update_or_create(
            user=request.user,
            game=GameResult.GAME_FRAMED,
            date=today,
            defaults={'score': score},
        )

    return JsonResponse({
        'correct': solved if not skip else False,
        'skip': skip,
        'game_over': game_over,
        'solved': solved,
        'attempts': len(guesses),
        'blur_filter': BLUR_LEVELS[blur_index],
        'answer': {
            'title': daily.film.title,
            'year': daily.film.release_date.year,
            'poster_path': daily.film.poster_path,
        } if game_over else None,
    })


def framed_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    films = (
        GameFilm.objects.filter(approved=True, title__icontains=q)
        .values('tmdb_id', 'title', 'release_date')[:8]
    )

    return JsonResponse({
        'results': [
            {
                'tmdb_id': f['tmdb_id'],
                'title': f['title'],
                'year': f['release_date'].year if f['release_date'] else '',
            }
            for f in films
        ]
    })
