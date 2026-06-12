#!/usr/bin/env python3
"""Hand-written Noosphere backfill — content composed by hand, not by an LLM.

These cards fill the recent gap with pieces written in a plainer, more personal
voice than the generators produce. They reuse the existing card types (and
therefore the existing renderers), so no frontend change is needed. All facts
are real and checkable.

Idempotent: skips any card whose feed file already exists. Discord cross-posting
is suppressed so a one-time backfill doesn't dump sixteen messages at once.

Run once from the noosphere root:  python3 seed_handwritten.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generators'))
from utils import write_feed, feed_exists  # noqa: E402

# (slug, card)  — slug becomes the feed filename; timestamp drives ordering.
CARDS = [
    # ── Untranslatable ────────────────────────────────────────────────
    ("2026-06-08-untranslatable-sobremesa", {
        "type": "untranslatable",
        "timestamp": "2026-06-08T14:00:00",
        "word": "sobremesa",
        "language": "Spanish",
        "content": "There's no English word for the hour that comes after the food is gone. The plates are pushed back, the wine is down to its last inch, nobody has anywhere to be — and the conversation, freed from the work of eating, finally gets good. Spanish calls this *sobremesa*, literally \"over-the-table.\" It isn't the meal and it isn't leaving; it's the soft third thing in between, where a lunch can quietly turn into an afternoon.\n\nThat English never bothered to name it says something about which culture decided this hour was worth defending. You can't schedule a sobremesa. You can only fail to end the meal, on purpose, together.",
        "question": "When did you last let a meal run long on purpose?"
    }),
    ("2026-06-11-untranslatable-toska", {
        "type": "untranslatable",
        "timestamp": "2026-06-11T14:30:00",
        "word": "тоска (toska)",
        "language": "Russian",
        "content": "Nabokov spent years dragging Russian into English and finally gave up on this one — he just listed its registers instead. At its deepest, *toska* is \"a sensation of great spiritual anguish, often without any specific cause.\" Lower down, \"a dull ache of the soul, a longing with nothing to long for.\" At its lightest, \"ennui, boredom.\" One word holds all of it, from grief to mild restlessness, the way a single grey holds every kind of weather.\n\nEnglish makes you pick: are you sad, or bored, or homesick, or just *off*? Russian lets you decline to choose. There's a strange mercy in a word that doesn't make you diagnose yourself before you're allowed to feel.",
        "question": "Is it kinder to have a name for the feeling, or to be spared one?"
    }),
    ("2026-06-12-untranslatable-escalier", {
        "type": "untranslatable",
        "timestamp": "2026-06-12T15:00:00",
        "word": "l'esprit de l'escalier",
        "language": "French",
        "content": "Diderot named it. You're at a dinner, someone says something that flattens you, you stand there blank — and then, halfway down the staircase on your way out, the perfect reply arrives, fully formed, useless. *L'esprit de l'escalier*: staircase wit. The mind works fine, it just keeps terrible hours.\n\nGerman, ever efficient, calques it straight across as *Treppenwitz*. English, tellingly, never named the experience, which is not the same as being spared it. Somewhere on every staircase in the world there is a person delivering, with devastating timing, the line they needed twenty seconds and one flight of stairs ago.",
        "question": "What did you finally think of, too late?"
    }),
    ("2026-06-10-untranslatable-mangata", {
        "type": "untranslatable",
        "timestamp": "2026-06-10T22:30:00",
        "word": "mångata",
        "language": "Swedish",
        "content": "The moon lays a road of light across the water, and Swedish has a word for the road: *mångata*, the moon-street. It only appears for the person looking. Stand somewhere else on the shore and the road quietly moves to meet you instead — which means no two people have ever stood on the same one.\n\nIt's a word for a thing that isn't really there: not the moon, not the water, just the angle between them and your eye. A whole noun built for a coincidence of geometry and attention. The most private piece of infrastructure in the world.",
        "question": None
    }),

    # ── The Dead Medium (renderer inserts content as raw HTML) ─────────
    ("2026-06-12-dead-medium-ceefax", {
        "type": "dead_medium",
        "timestamp": "2026-06-12T17:00:00",
        "title": "Ceefax",
        "dates": "1974 – 2012",
        "content": "Before the web there was teletext: the news hidden inside the television signal itself, tucked into the black gaps between the picture lines. You typed a three-digit page number on the remote and waited — the page didn't load so much as <em>cycle around</em> to you, like a paternoster lift, and if you were too slow you watched it sail past and had to wait for it to come back. P101 for headlines. P302 for football. P401 for the weather, drawn in blocky coloured squares.<br><br>The BBC's Ceefax ran for thirty-eight years and died at 23:32 on 23 October 2012, when the last analogue transmitter in Northern Ireland switched off. It had no scroll, no search, no comments, and no refresh. You waited your turn, and the news arrived in its own time — which sounds less like a limitation now than a kind of patience we've misplaced."
    }),
    ("2026-06-06-dead-medium-pneumatic", {
        "type": "dead_medium",
        "timestamp": "2026-06-06T17:30:00",
        "title": "The Paris Pneumatic Post",
        "dates": "1866 – 1984",
        "content": "For over a century Paris ran a second postal system underneath the first one — a network of iron tubes beneath the streets, some 467 kilometres of them at its peak, through which little canisters of letters were fired by compressed air. You wrote your message on a special blue card, a <em>petit bleu</em>, dropped it at the post office, and it was blown across the city to arrive in under two hours, decades before anyone dreamed of email.<br><br>The system closed on 30 March 1984, killed first by the telephone and then by the fax. There is something almost unbearably tender about a city that, for a hundred years, physically blew people's love letters through pipes under the feet of everyone walking above."
    }),

    # ── Typeface of the Week ───────────────────────────────────────────
    ("2026-06-10-typeface-doves", {
        "type": "typeface",
        "timestamp": "2026-06-10T12:00:00",
        "font_name": "Doves Type",
        "content": "The Doves Press made exactly one typeface, and it was so beautiful that its two founders went to war over who would own it. When the partnership collapsed, T. J. Cobden-Sanderson decided that if he couldn't have it, no one would. Across 1916 and 1917, in more than a hundred late-night trips, a man in his seventies carried the entire foundry — the punches, the matrices, the cast metal type — to Hammersmith Bridge and dropped it, piece by piece, into the Thames.\n\nFor a century the type survived only on the printed page, drowned but not quite dead. Then in 2014 a designer named Robert Green hired divers, recovered around 150 pieces of the original metal from the riverbed, and used them to rebuild the digital font you can now, improbably, just download. A typeface thrown into a river out of spite, and fished back out by love, ninety-eight years later.",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Doves_Type"
    }),
    ("2026-06-06-typeface-comic-sans", {
        "type": "typeface",
        "timestamp": "2026-06-06T12:30:00",
        "font_name": "Comic Sans",
        "content": "The most hated typeface in the world began as an act of kindness. In 1994 Vincent Connare was at Microsoft, looking at a beta of a children's program called Microsoft Bob, in which a cartoon dog spoke to you — in Times New Roman. A dog, talking in the typeface of *The Times of London*. It was absurd, so Connare pulled the comic books off his desk, *Watchmen* and *The Dark Knight Returns*, and drew a font that looked like a friendly human hand.\n\nIt was never supposed to leave the dog. Then it shipped with Windows, and a planet's worth of people reached past Helvetica and Garamond for the one typeface that felt *warm* — and used it for everything: bake sales, funeral notices, hospital signage. The design world has been embarrassed ever since. But people don't choose Comic Sans because they have bad taste. They choose it because it's the only font that ever smiled at them.",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Comic_Sans"
    }),

    # ── The Penny Red ──────────────────────────────────────────────────
    ("2026-06-07-penny-red-petersburg", {
        "type": "penny_red",
        "timestamp": "2026-06-07T11:30:00",
        "former_name": "Petrograd · Leningrad",
        "current_name": "Saint Petersburg",
        "country": "Russia",
        "content": "Few cities have argued with their own name this much. Peter the Great founded it in 1703 and gave it a German-Dutch name, *Sankt-Peterburg*, because he wanted a window onto Europe. In 1914, the week war with Germany began, the German was hastily scrubbed off and it became *Petrograd* — same saint, Slavic suffix. Ten years later Lenin died and it became *Leningrad*, and under that name it starved through 872 days of siege and did not fall.\n\nThen in 1991 the city voted, narrowly, to take its first name back. So the war memorials still say Leningrad, the grandmothers sometimes still say Leningrad, and the road signs say Saint Petersburg. A place can wear all its names at once. The old ones don't wash off — they sink under the new paint and show through."
    }),
    ("2026-06-09-penny-red-konigsberg", {
        "type": "penny_red",
        "timestamp": "2026-06-09T11:00:00",
        "former_name": "Königsberg",
        "current_name": "Kaliningrad",
        "country": "Russia (formerly East Prussia)",
        "content": "Königsberg gave the world two perfect things and then stopped existing. The first was a puzzle: seven bridges over the river Pregel, and the question of whether you could cross all of them exactly once. In 1736 Leonhard Euler proved you couldn't — and in proving it, invented graph theory, the math that now routes your packets and your subway trains. The second was Immanuel Kant, who was born there, taught there, and is said never to have travelled more than a hundred miles from it. The city was his whole world, and from it he reasoned out the shape of all possible worlds.\n\nIn 1946, the year after the war flattened it, the Soviet Union renamed it Kaliningrad, after a Bolshevik functionary most Russians couldn't pick out of a lineup. The German population was gone; the name went with them. Kant's tomb survived — which is how you can still stand in a Russian city, beside a Prussian philosopher, on the bank of a river whose bridges taught the world to count its own paths."
    }),

    # ── The Diff (texts inserted as raw HTML; commentary via md2html) ──
    ("2026-06-08-the-diff-letranger", {
        "type": "the_diff",
        "timestamp": "2026-06-08T09:30:00",
        "title": "The first line of L'Étranger",
        "texts": [
            {"lang": "French", "text": "Aujourd'hui, maman est morte. Ou peut-être hier, je ne sais pas."},
            {"lang": "English · Gilbert, 1946", "text": "Mother died today. Or, maybe, yesterday; I can't be sure."},
            {"lang": "English · Ward, 1988", "text": "Maman died today. Or yesterday maybe, I don't know."}
        ],
        "commentary": "Camus opens *The Stranger* with four words, and translators have argued about one of them for eighty years. *Maman* is not \"Mother.\" \"Mother\" is what you call her at the funeral, in a black suit, at a careful distance — it's the word Stuart Gilbert reached for in 1946, and it quietly makes Meursault colder and more grown than the French does. But *maman* is a child's word, *mum*, warm and small, and Meursault — this man everyone calls unfeeling — uses it. Matthew Ward, in 1988, finally refused to translate it at all and left *Maman* sitting in the English like an untranslated nerve.\n\nThe whole novel is in that gap: a man too honest to perform grief, using the most intimate word he has for his dead mother, in a language that keeps trying to make him sound like he doesn't care. The translator's real job here isn't to find the English for *maman*. It's to decide who Meursault is — and the very first word commits you."
    }),

    # ── Apophenia (item content + connection are escaped → plain text) ─
    ("2026-06-11-apophenia-voynich", {
        "type": "apophenia",
        "timestamp": "2026-06-11T15:30:00",
        "item_a": {
            "type": "manuscript",
            "content": "The Voynich Manuscript: 240 pages from the early 1400s, written in a fluent, looping, entirely unknown script and illustrated with plants that don't exist and star charts of no known sky. Every statistical test says it behaves like real language — consistent word-frequency laws, recurring structure — yet in six hundred years no one has read a single sentence of it."
        },
        "item_b": {
            "type": "technology",
            "content": "A language model confidently producing a citation: author, journal, volume, page numbers, a DOI, all formatted flawlessly, all completely invented. The exact shape of a fact, with nothing inside it."
        },
        "connection": "Both are fluent without being true — language that has learned the form of meaning so well it no longer needs the content. The Voynich may be an elaborate 15th-century hoax: glossolalia with grammar, written to look precisely like knowledge. Six hundred years apart, a scribe and a model independently found the same uncanny trick: get the surface texture of sense right enough, and people will sit and stare at it for centuries, certain there must be something underneath.",
        "prompt": "What connects these?"
    }),
    ("2026-06-09-apophenia-sourdough", {
        "type": "apophenia",
        "timestamp": "2026-06-09T16:00:00",
        "item_a": {
            "type": "living thing",
            "content": "A sourdough starter: flour, water, and the wild yeast that drifted in from someone's kitchen air, kept alive by being fed a little every day. Some bakeries still pour from starters more than a hundred years old — the same continuous culture, never once the same molecule twice."
        },
        "item_b": {
            "type": "text",
            "content": "A manuscript tradition: a Greek play we can still read only because a monk copied it from a scroll that was copied from a scroll, for a thousand years, each scribe replacing the last as the parchment rotted out from under the words."
        },
        "connection": "Neither survives by lasting. The starter is not old flour; the play is not old parchment — every physical atom has been swapped out many times over. What persists is the pattern, handed forward by daily tending, alive only as long as someone keeps copying it into fresh material. Lose the habit for a month and the starter dies; lose the scribes for a generation and the text is gone. Both are proof that some things can only exist as verbs.",
        "prompt": "What connects these?"
    }),

    # ── The Annotation Layer (sup markers, like the real cards) ────────
    ("2026-06-07-annotation-james", {
        "type": "annotation",
        "timestamp": "2026-06-07T15:00:00",
        "text": "Consciousness, then, does not appear to itself chopped up in bits.<sup class=\"ann-marker\">1</sup> Such words as 'chain' or 'train' do not describe it fitly as it presents itself in the first instance. It is nothing jointed; it flows.<sup class=\"ann-marker\">2</sup> A 'river' or a 'stream' are the metaphors by which it is most naturally described.<sup class=\"ann-marker\">3</sup>",
        "annotations": [
            "<strong>chopped up in bits</strong> — James is arguing against his own century's psychology, which treated the mind as a chain of discrete 'ideas' clicking past like train cars. He wants you to notice that you have never once felt one thought <em>end</em> and the next one <em>begin</em>.",
            "<strong>it flows</strong> — three words that renamed a feeling. Everything we now call 'stream of consciousness' — Woolf, Joyce, the whole interior monologue — uncoils from this verb. He didn't discover the thing; he found the metaphor that let novelists go looking for it.",
            "<strong>a 'river' or a 'stream'</strong> — note he reaches for water, not wind or fire: a mind with a current and a direction, that you can fall into, that drowns you if you stop swimming. We've believed the metaphor so completely we forget it was ever a choice."
        ],
        "source": "William James, <em>The Principles of Psychology</em> (1890)"
    }),
]


def main():
    written = 0
    for slug, card in CARDS:
        if feed_exists(slug):
            print(f"  skip (exists): {slug}")
            continue
        write_feed(slug, card, post_discord=False)
        written += 1
    print(f"\nBackfill complete: {written} new card(s), {len(CARDS) - written} already present.")


if __name__ == '__main__':
    main()
