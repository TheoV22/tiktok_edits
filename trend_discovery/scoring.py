from typing import List, Dict
import random
from datetime import datetime

def score_shorts(shorts: List[Dict], temperature=0.5) -> List[Dict]:
    """
    Score shorts using multi-factor algorithm.
    
    Factors:
    - 40% views (normalized to max views in set)
    - 30% engagement rate (likes/views)
    - 20% recency (recent uploads prioritized)
    - 10% uniqueness (less saturated songs get bonus)
    
    Returns sorted list (highest score first)
    """
    if not shorts:
        return []
    
    # Calculate max values for normalization
    max_views = max(s.get('view_count', 1) for s in shorts)
    
    # Track song frequency for uniqueness bonus
    song_counts = {}
    for short in shorts:
        song_key = f"{short.get('sound_title', '')}_{short.get('sound_author', '')}"
        song_counts[song_key] = song_counts.get(song_key, 0) + 1
    
    # Score each short
    for short in shorts:
        score = 0.0
        
        # 1. Views (40% weight)
        views = short.get('view_count', 0)
        view_score = (views / max_views) if max_views > 0 else 0
        score += view_score * 0.4
        
        # 2. Engagement rate (30% weight)
        likes = short.get('like_count', 0)
        if views > 0:
            engagement = likes / views
            engagement_score = min(1.0, engagement / 0.15)  # 15% is excellent
            score += engagement_score * 0.3
        
        # 3. Recency (20% weight)
        upload_date = short.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            try:
                upload_dt = datetime.strptime(upload_date, '%Y%m%d')
                days_old = (datetime.now() - upload_dt).days
                
                if days_old <= 7:
                    recency_score = 1.0
                elif days_old <= 30:
                    recency_score = 0.8
                elif days_old <= 90:
                    recency_score = 0.5
                else:
                    recency_score = 0.2
                
                score += recency_score * 0.2
            except:
                score += 0.1
        else:
            score += 0.1
        
        # 4. Uniqueness (10% weight)
        song_key = f"{short.get('sound_title', '')}_{short.get('sound_author', '')}"
        song_count = song_counts.get(song_key, 1)
        uniqueness_score = 1.0 / song_count  # Less saturated = higher score
        score += uniqueness_score * 0.1
        
        short['final_score'] = score
    
    # Sort by score (highest first)
    shorts.sort(key=lambda x: x.get('final_score', 0), reverse=True)
    
    return shorts


def select_diverse_content(scored_shorts: List[Dict], temperature=0.5) -> Dict:
    """
    Select anime and songs with temperature-based diversity control.
    
    Temperature effects:
    - Low (0-0.3): 1 anime (focused)
    - Medium (0.4-0.6): 2 anime (balanced)
    - High (0.7-1.0): 3 anime (diverse)
    
    Always selects 1 song (most popular from selected anime)
    
    Returns:
        {
            'animes': [anime_title1, ...],
            'song': {video metadata of best short},
            'source_shorts': [list of shorts used]
        }
    """
    if not scored_shorts:
        return {'animes': [], 'song': None, 'source_shorts': []}
    
    # Determine anime count based on temperature
    if temperature < 0.4:
        anime_count = 1
    elif temperature < 0.7:
        anime_count = 2
    else:
        anime_count = 3
    
    # Group shorts by anime
    anime_groups = {}
    for short in scored_shorts:
        anime_title = short.get('anime_title', 'Unknown')
        if anime_title not in anime_groups:
            anime_groups[anime_title] = []
        anime_groups[anime_title].append(short)
    
    # Select top anime based on best short in each  
    anime_scores = []
    for anime_title, shorts in anime_groups.items():
        best_score = max(s.get('final_score', 0) for s in shorts)
        anime_scores.append((anime_title, best_score, shorts))
    
    anime_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select top N anime with temperature-based sampling
    selected_anime = []
    selected_shorts = []
    
    if temperature < 0.4:
        # Low temp: always pick top
        selected_anime = [anime_scores[0][0]]
        selected_shorts.extend(anime_scores[0][2])
    elif temperature < 0.7:
        # Medium temp: weighted sampling from top 5
        top_n = min(5, len(anime_scores))
        weights = [anime_scores[i][1] for i in range(top_n)]
        sampled_indices = random.choices(range(top_n), weights=weights, k=min(2, len(anime_scores)))
        for idx in sampled_indices:
            if anime_scores[idx][0] not in selected_anime:
                selected_anime.append(anime_scores[idx][0])
                selected_shorts.extend(anime_scores[idx][2])
    else:
        # High temp: random from top 10
        top_n = min(10, len(anime_scores))
        sampled = random.sample(anime_scores[:top_n], min(3, len(anime_scores)))
        for anime_title, score, shorts in sampled:
            selected_anime.append(anime_title)
            selected_shorts.extend(shorts)
    
    # Select best song from selected anime shorts
    selected_shorts.sort(key=lambda x: x.get('final_score', 0), reverse=True)
    best_short = selected_shorts[0] if selected_shorts else None
    
    return {
        'animes': selected_anime,
        'song': best_short,
        'source_shorts': selected_shorts
    }
