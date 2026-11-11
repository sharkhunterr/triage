import { useQuery } from '@tanstack/react-query'
import { Images } from 'lucide-react'
import { api, type Schemas } from '../../api/client'
import { Spinner } from '../../design-system'
import { useT } from '../../i18n'

type MovieMedia = Schemas['MovieMedia']

const IMAGE = 'https://image.tmdb.org/t/p'

/** A few TMDB stills, to see at a glance whether Radarr matched the right movie. Read apart from
 * the decision: the page shows without them when TMDB is down. */
export function MatchCheck({ radarrId }: { radarrId: number }) {
  const t = useT()
  const media = useQuery({
    queryKey: ['movie-media', radarrId],
    queryFn: () => api<MovieMedia>(`/movies/${radarrId}/media`),
    staleTime: 60_000,
  })
  const images = media.data?.images ?? []
  return (
    <section className="flex flex-col gap-3" aria-labelledby="match-check">
      <h3 id="match-check" className="flex items-center gap-2 font-semibold">
        <Images className="size-4" aria-hidden /> {t('match.title')}
      </h3>
      {media.isPending ? (
        <Spinner label={t('common.loading')} />
      ) : images.length === 0 ? (
        <p className="text-sm text-muted">{t('match.noImages')}</p>
      ) : (
        <ul className="-mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-1">
          {images.map((path, i) => (
            <li key={path} className="shrink-0 snap-start">
              <a href={`${IMAGE}/w1280${path}`} target="_blank" rel="noreferrer" className="block">
                <img
                  src={`${IMAGE}/w300${path}`}
                  alt={t('match.still', { n: i + 1 })}
                  loading="lazy"
                  className="aspect-video w-44 rounded-md bg-surface-2 object-cover sm:w-52"
                />
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
