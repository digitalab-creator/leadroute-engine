const CITE_SPLIT = /(\[(BC-\d+[a-z]?|PP-\d+)\])/;

type BriefProseProps = {
  text: string;
};

/** Renders brief text with BC/PP claim ids as small tags (not errors). */
export function BriefProse({ text }: BriefProseProps) {
  const parts = text.split(CITE_SPLIT);
  return (
    <>
      {parts.map((part, index) => {
        const tag = part.match(/^\[(BC-\d+[a-z]?|PP-\d+)\]$/);
        if (tag) {
          return (
            <span
              key={`${index}-${tag[1]}`}
              className="cite-id"
              title="Approved claim id from brand context"
            >
              {tag[1]}
            </span>
          );
        }
        return part ? <span key={index}>{part}</span> : null;
      })}
    </>
  );
}
