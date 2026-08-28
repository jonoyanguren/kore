type Props = {
  on: boolean
}

export function StarIcon({ on }: Props) {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        d="M12 2.5l2.9 5.88 6.5.95-4.7 4.58 1.11 6.47L12 17.27 6.19 20.38 7.3 13.9 2.6 9.33l6.5-.95L12 2.5z"
        fill={on ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth={on ? 0 : 1.8}
        strokeLinejoin="round"
      />
    </svg>
  )
}
