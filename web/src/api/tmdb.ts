import { api } from './client'

export interface TmdbItem {
  id: number
  title: string
  type: 'tv' | 'movie'
  year: number | null
  release_date: string
  vote_average: number
  overview: string
  poster_url: string | null
  backdrop_url: string | null
  popularity?: number
  seasons?: Array<{ season_number: number; name: string; episode_count: number; poster_url: string | null }>
}

export const tmdbApi = {
  trending: () => api<TmdbItem[]>('/api/v1/tmdb/trending'),
  popularTv: () => api<TmdbItem[]>('/api/v1/tmdb/popular/tv'),
  popularMovies: () => api<TmdbItem[]>('/api/v1/tmdb/popular/movies'),
  douban: (rank: 'showing' | 'movie_hot' | 'tv_hot') => api<TmdbItem[]>(`/api/v1/tmdb/douban/${rank}`),
  bangumiCalendar: () => api<TmdbItem[]>('/api/v1/tmdb/bangumi/calendar'),
  anilistSeason: () => api<TmdbItem[]>('/api/v1/tmdb/anilist/season'),
  search: (query: string) => api<TmdbItem[]>(`/api/v1/tmdb/search?query=${encodeURIComponent(query)}`),
  detail: (type: string, id: number) => api<TmdbItem>(`/api/v1/tmdb/detail/${type}/${id}`),
}
