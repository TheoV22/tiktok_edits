import re
from typing import List, Dict, Tuple
from datetime import datetime

def _extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text."""
    return re.findall(r'#(\w+)', text)

def _enhanced_song_extraction(title: str, description: str) -> Tuple[str, str]:
    """
    Enhanced song extraction using multiple patterns and fallbacks.
    Tries title first, then description.
    Returns (song_title, artist).
    """
    # Try extracting from title first
    song, artist = _extract_song_from_title(title)
    
    # If extraction failed or looks generic, try description
    if artist == "Unknown" and description:
        desc_song, desc_artist = _extract_song_from_title(description.split('\n')[0])
        if desc_artist != "Unknown":
            return desc_song, desc_artist
    
    return song, artist

def _extract_song_from_title(title: str) -> Tuple[str, str]:
    """
    Extract song name and artist from video title using multiple patterns.
    Returns (song_title, artist).
    """
    # Known artists database for better matching
    known_artists = {
        'kordhell', 'dxrk', 'shadowraze', 'playaphonk', 'dvrst', 
        'pharmacist', 'interworld', 'dxrk ダーク', 'lxst cxntury',
        'montagem', 'slowed', 'sped up'
    }
    
    # Pattern 1: "Song - Artist" or "Artist - Song"
    match = re.search(r'^([^-|\[]+?)\s*[-–]\s*([^|\[]+?)(?:\s*[\|\[]|$)', title, re.IGNORECASE)
    if match:
        part1, part2 = match.group(1).strip(), match.group(2).strip()
        
        # Check if either part contains known artist
        part1_lower = part1.lower()
        part2_lower = part2.lower()
        
        for artist in known_artists:
            if artist in part1_lower:
                return part2, part1
            if artist in part2_lower:
                return part1, part2
        
        # If no known artist, assume "Artist - Song" format
        if 'edit' in part1_lower or 'amv' in part1_lower:
            return part1, part2
        return part2, part1
    
    # Pattern 2: "Song by Artist"
    match = re.search(r'["\']?([^"\']+?)["\']?\s+by\s+([^|\[\n]+)', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Pattern 3: "Artist × Song" or "Artist x Song"
    match = re.search(r'([^×x\[]+?)\s*[×x]\s*([^|\[\n]+)', title, re.IGNORECASE)
    if match:
        return match.group(2).strip(), match.group(1).strip()
    
    # Pattern 4: "Song ft. Artist" or "Song feat. Artist"
    match = re.search(r'([^(]+?)\s*(?:ft\.?|feat\.?)\s*([^)|\[\n]+)', title, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Fallback: return title as song, Unknown as artist
    # Clean up common suffixes
    clean_title = re.sub(r'\s*[\|\[].*$', '', title)
    clean_title = re.sub(r'\s*\(.*?\)', '', clean_title)
    clean_title = clean_title.strip()
    
    return clean_title, "Unknown"

def _calculate_trending_score(
    view_count: int,
    like_count: int,
    upload_date: str,
    duration: float = None
) -> float:
    """
    Calculate trending score from multiple signals.
    Returns score in 0-1 range, higher is more trending.
    """
    score = 0.0
    
    # Component 1: View count (50% weight)
    # Normalize: 100K views = 0.25, 500K = 0.5, 1M+ = 1.0
    view_score = min(1.0, view_count / 1000000) if view_count else 0.0
    score += view_score * 0.5
    
    # Component 2: Engagement rate (30% weight)
    if view_count and view_count > 0:
        engagement_rate = like_count / view_count
        # Good engagement is ~5-10%, cap at 15%
        engagement_score = min(1.0, engagement_rate / 0.15)
        score += engagement_score * 0.3
    
    # Component 3: Recency (20% weight)
    try:
        if upload_date and len(upload_date) == 8:
            upload_dt = datetime.strptime(upload_date, '%Y%m%d')
            days_old = (datetime.now() - upload_dt).days
            
            # Heavily favor recent uploads
            if days_old <= 7:
                recency_score = 1.0
            elif days_old <= 30:
                recency_score = 0.8
            elif days_old <= 90:
                recency_score = 0.5
            else:
                recency_score = 0.2
            
            score += recency_score * 0.2
        else:
            score += 0.1  # Default if no date
    except:
        score += 0.1  # Default if parsing fails
    
    return min(1.0, max(0.0, score))

def _get_popular_phonk_songs() -> List[Dict]:
    """Returns list of popular phonk/edit songs for pairing with anime."""
    return [
        {
            "id": "kordhell_murder",
            "title": "Murder In My Mind",
            "author": "Kordhell",
            "url": "https://www.youtube.com/watch?v=w-sQRS-Lc9k",
            "vibe": "high_energy"  # Action, epic
        },
        {
            "id": "dxrk_rave",
            "title": "RAVE",
            "author": "Dxrk",
            "url": "https://www.youtube.com/watch?v=VBB1S22vdEI",
            "vibe": "high_energy"  # Action, intense
        },
        {
            "id": "kordhell_live",
            "title": "Live Another Day",
            "author": "Kordhell",
            "url": "https://www.youtube.com/watch?v=VhB-3LvqJ3o",
            "vibe": "epic"  # Fantasy, adventure
        },
        {
            "id": "shadowraze_funk",
            "title": "Funk Estranho",
            "author": "SHADOWRAZE",
            "url": "https://www.youtube.com/watch?v=jvwXqT9MTVU",
            "vibe": "dark"  # Dark, thriller
        },
        {
            "id": "playaphonk_phonky",
            "title": "PHONKY TOWN",
            "author": "PlayaPhonk",
            "url": "https://www.youtube.com/watch?v=7w-YjHHPh7I",
            "vibe": "chill"  # Slice of life, calm
        },
        {
            "id": "dvrst_close_eyes",
            "title": "Close Eyes",
            "author": "DVRST",
            "url": "https://www.youtube.com/watch?v=ao4RCon11eY",
            "vibe": "dark"  # Dark, mystery
        }
    ]

def _match_anime_to_song(genres: List[str], anime_title: str) -> Dict:
    """
    Match anime genres to appropriate phonk song vibe.
    Returns a song dictionary.
    """
    songs = _get_popular_phonk_songs()
    
    # Convert genres to lowercase for matching
    genres_lower = [g.lower() for g in genres]
    title_lower = anime_title.lower()
    
    # Genre-to-vibe mapping
    if any(g in genres_lower for g in ['action', 'shounen', 'super power', 'martial arts']):
        vibe = "high_energy"
    elif any(g in genres_lower for g in ['thriller', 'horror', 'mystery', 'psychological']):
        vibe = "dark"
    elif any(g in genres_lower for g in ['fantasy', 'adventure', 'supernatural']):
        vibe = "epic"
    elif any(g in genres_lower for g in ['slice of life', 'comedy', 'romance']):
        vibe = "chill"
    else:
        # Default to high_energy for unknown genres (most anime edits are action-focused)
        vibe = "high_energy"
    
    # Also check title for hints if no genres provided
    if not genres:
        if any(word in title_lower for word in ['demon', 'slayer', 'attack', 'hero', 'fight']):
            vibe = "high_energy"
        elif any(word in title_lower for word in ['death', 'dark', 'monster']):
            vibe = "dark"
    
    # Find matching songs by vibe
    matching_songs = [s for s in songs if s.get('vibe') == vibe]
    
    if matching_songs:
        # Use hash of anime title to consistently pick same song for same anime
        import hashlib
        hash_val = int(hashlib.md5(anime_title.encode()).hexdigest(), 16)
        return matching_songs[hash_val % len(matching_songs)]
    
    # Fallback to first song
    return songs[0]

def _get_hardcoded_tracks() -> List[Dict]:
    """Final fallback: returns curated list of proven anime edit tracks."""
    songs = _get_popular_phonk_songs()
    
    videos = []
    for song in songs:
        metadata = {
            "video_id": song['id'],
            "video_url": song['url'],
            "sound_id": song['id'],
            "sound_title": song['title'],
            "sound_author": song['author'],
            "caption": f"Anime Edit - {song['title']}",
            "play_url": "",
            "source": "fallback",
            "trending_score": 0.5
        }
        videos.append(metadata)
    
    return videos
