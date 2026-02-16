#!/usr/bin/env python3
"""The Diff — the same passage in two (or three) languages, side by side.

Uses real public domain translations from Project Gutenberg + curated pairs.
Highlights what changes in translation — what each language must say, can't say, or chooses to say differently.
"""
import json, os, random
from utils import ask_claude, today, write_feed, feed_exists

# Curated parallel passages — famous texts where translation reveals something
PAIRS = [
    {
        "title": "Genesis 1:1",
        "texts": [
            {"lang": "Hebrew", "text": "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃"},
            {"lang": "English (KJV)", "text": "In the beginning God created the heaven and the earth."},
            {"lang": "Russian (Synodal)", "text": "В начале сотворил Бог небо и землю."},
        ],
    },
    {
        "title": "The Little Prince, Ch. 21",
        "texts": [
            {"lang": "French", "text": "«On ne voit bien qu'avec le cœur. L'essentiel est invisible pour les yeux.»"},
            {"lang": "English", "text": "\"One sees clearly only with the heart. What is essential is invisible to the eye.\""},
            {"lang": "Russian", "text": "«Зорко одно лишь сердце. Самого главного глазами не увидишь.»"},
        ],
    },
    {
        "title": "Anna Karenina, opening line",
        "texts": [
            {"lang": "Russian", "text": "Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему."},
            {"lang": "English (Garnett)", "text": "Happy families are all alike; every unhappy family is unhappy in its own way."},
            {"lang": "English (Pevear/Volokhonsky)", "text": "All happy families are alike; each unhappy family is unhappy in its own way."},
        ],
    },
    {
        "title": "The Odyssey, opening lines",
        "texts": [
            {"lang": "Greek", "text": "Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ πλάγχθη..."},
            {"lang": "English (Fagles)", "text": "Sing to me of the man, Muse, the man of twists and turns driven time and again off course..."},
            {"lang": "English (Wilson)", "text": "Tell me about a complicated man. Muse, tell me how he wandered and was lost..."},
        ],
    },
    {
        "title": "Hamlet, Act III, Scene 1",
        "texts": [
            {"lang": "English", "text": "To be, or not to be, that is the question."},
            {"lang": "Russian (Pasternak)", "text": "Быть или не быть, вот в чём вопрос."},
            {"lang": "German (Schlegel)", "text": "Sein oder Nichtsein, das ist hier die Frage."},
            {"lang": "French (Hugo)", "text": "Être ou ne pas être, c'est là la question."},
        ],
    },
    {
        "title": "Don Quixote, opening line",
        "texts": [
            {"lang": "Spanish", "text": "En un lugar de la Mancha, de cuyo nombre no quiero acordarme..."},
            {"lang": "English (Grossman)", "text": "Somewhere in La Mancha, in a place whose name I do not care to remember..."},
            {"lang": "English (Raffel)", "text": "In a village in La Mancha, the name of which I cannot quite recall..."},
        ],
    },
    {
        "title": "The Metamorphosis, opening line",
        "texts": [
            {"lang": "German", "text": "Als Gregor Samsa eines Morgens aus unruhigen Träumen erwachte, fand er sich in seinem Bett zu einem ungeheueren Ungeziefer verwandelt."},
            {"lang": "English (Muir)", "text": "As Gregor Samsa awoke one morning from uneasy dreams he found himself transformed in his bed into a gigantic insect."},
            {"lang": "English (Bernofsky)", "text": "One morning, as Gregor Samsa was waking up from anxious dreams, he discovered that in bed he had been changed into a monstrous verminous bug."},
        ],
    },
    {
        "title": "Crime and Punishment, opening line",
        "texts": [
            {"lang": "Russian", "text": "В начале июля, в чрезвычайно жаркое время, под вечер, молодой человек вышел из своей каморки, которую нанимал от жильцов в С-м переулке, на улицу и медленно, как бы в нерешимости, отправился к К-ну мосту."},
            {"lang": "English (Garnett)", "text": "On an exceptionally hot evening early in July, a young man came out of the garret in which he lodged in S. Place and walked slowly, as though in hesitation, towards K. bridge."},
            {"lang": "English (Pevear/Volokhonsky)", "text": "At the beginning of July, during an extremely hot spell, towards evening, a young man left the closet he rented from tenants in S——y Lane, walked out to the street, and slowly, as if indecisively, headed for K——n Bridge."},
        ],
    },
    {
        "title": "One Hundred Years of Solitude, opening line",
        "texts": [
            {"lang": "Spanish", "text": "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar aquella tarde remota en que su padre lo llevó a conocer el hielo."},
            {"lang": "English (Rabassa)", "text": "Many years later, as he faced the firing squad, Colonel Aureliano Buendía was to remember that distant afternoon when his father took him to discover ice."},
        ],
    },
    {
        "title": "Rilke, Duino Elegies (First Elegy)",
        "texts": [
            {"lang": "German", "text": "Wer, wenn ich schriee, hörte mich denn aus der Engel Ordnungen?"},
            {"lang": "English (Mitchell)", "text": "Who, if I cried out, would hear me among the angels' hierarchies?"},
            {"lang": "English (Leishman/Spender)", "text": "Who, if I cried, would hear me among the angelic orders?"},
        ],
    },
    {
        "title": "The Master and Margarita, Ch. 1",
        "texts": [
            {"lang": "Russian", "text": "«Никогда не разговаривайте с неизвестными.»"},
            {"lang": "English (Ginsburg)", "text": "\"Never talk to strangers.\""},
            {"lang": "English (Pevear/Volokhonsky)", "text": "\"Never speak with unknown people.\""},
        ],
    },
    {
        "title": "Camus, The Stranger, opening line",
        "texts": [
            {"lang": "French", "text": "Aujourd'hui, maman est morte."},
            {"lang": "English (Stuart Gilbert)", "text": "Mother died today."},
            {"lang": "English (Matthew Ward)", "text": "Maman died today."},
        ],
    },
    {
        "title": "Proust, Swann's Way, opening line",
        "texts": [
            {"lang": "French", "text": "Longtemps, je me suis couché de bonne heure."},
            {"lang": "English (Moncrieff)", "text": "For a long time I used to go to bed early."},
            {"lang": "English (Davis)", "text": "For a long time, I went to bed early."},
        ],
    },
    {
        "title": "Dante, Inferno, Canto I",
        "texts": [
            {"lang": "Italian", "text": "Nel mezzo del cammin di nostra vita / mi ritrovai per una selva oscura, / ché la diritta via era smarrita."},
            {"lang": "English (Longfellow)", "text": "Midway upon the journey of our life / I found myself within a forest dark, / For the straightforward pathway had been lost."},
            {"lang": "English (Ciardi)", "text": "Midway in our life's journey, I went astray / from the straight road and woke to find myself / alone in a dark wood."},
        ],
    },
    {
        "title": "Neruda, Poem 20 (Veinte poemas de amor)",
        "texts": [
            {"lang": "Spanish", "text": "Puedo escribir los versos más tristes esta noche. / Escribir, por ejemplo: «La noche está estrellada, / y tiritan, azules, los astros, a lo lejos.»"},
            {"lang": "English (W.S. Merwin)", "text": "Tonight I can write the saddest lines. / Write, for example, 'The night is starry / and the stars are blue and shiver in the distance.'"},
        ],
    },
    {
        "title": "Rumi, Masnavi, opening lines",
        "texts": [
            {"lang": "Persian", "text": "بشنو از نی چون حکایت می‌کند / از جدایی‌ها شکایت می‌کند"},
            {"lang": "English (Barks)", "text": "Listen to the story told by the reed, / of being separated."},
            {"lang": "English (Nicholson)", "text": "Hearken to the reed-flute, how it complains, / bewailing its banishment from its home."},
        ],
    },
    {
        "title": "Bashō, most famous haiku",
        "texts": [
            {"lang": "Japanese", "text": "古池や蛙飛びこむ水の音"},
            {"lang": "English (Blyth)", "text": "The old pond; / A frog jumps in — / The sound of the water."},
            {"lang": "English (Hass)", "text": "Old pond . . . / a frog jumps in / water's sound"},
        ],
    },
    {
        "title": "Eugene Onegin, Ch. 1, Stanza I",
        "texts": [
            {"lang": "Russian", "text": "Мой дядя самых честных правил, / Когда не в шутку занемог, / Он уважать себя заставил / И лучше выдумать не мог."},
            {"lang": "English (Nabokov)", "text": "My uncle has most honest principles: / when taken ill in earnest, / he has made one respect him / and nothing better could invent."},
            {"lang": "English (Johnston)", "text": "My uncle — Loss functions of the highest — / When he fell ill beyond repair, / Forced everyone to hold him highest / And couldn't have pulled a shrewder snare."},
        ],
    },
    {
        "title": "Tao Te Ching, opening lines",
        "texts": [
            {"lang": "Chinese", "text": "道可道，非常道。名可名，非常名。"},
            {"lang": "English (Legge)", "text": "The Tao that can be trodden is not the enduring and unchanging Tao. The name that can be named is not the enduring and unchanging name."},
            {"lang": "English (Mitchell)", "text": "The tao that can be told is not the eternal Tao. The name that can be named is not the eternal Name."},
            {"lang": "English (Ursula Le Guin)", "text": "The way you can go isn't the real way. The name you can say isn't the real name."},
        ],
    },
    {
        "title": "War and Peace, opening line",
        "texts": [
            {"lang": "Russian/French", "text": "«Eh bien, mon prince. Gênes et Lucques ne sont plus que des apanages, des поместья, de la famille Buonaparte.»"},
            {"lang": "English (Maude)", "text": "\"Well, Prince, so Genoa and Lucca are now just family estates of the Buonapartes.\""},
            {"lang": "English (Briggs)", "text": "\"Well, Prince, Genoa and Lucca are now no more than estates, private estates, of the Bonaparte family.\""},
        ],
    },
]

STATE_FILE = os.path.join(os.path.dirname(__file__), '.diff-state.json')

def get_next_pair():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    used = set(state.get('used', []))
    available = [i for i in range(len(PAIRS)) if i not in used]
    if not available:
        used = set()
        available = list(range(len(PAIRS)))
    idx = random.choice(available)
    used.add(idx)
    with open(STATE_FILE, 'w') as f:
        json.dump({'used': list(used)}, f)
    return PAIRS[idx]

def generate():
    name = f"{today()}-the-diff"
    if feed_exists(name):
        print(f"Already exists: {name}")
        return

    pair = get_next_pair()

    texts_formatted = "\n\n".join([f"[{t['lang']}]: \"{t['text']}\"" for t in pair['texts']])

    prompt = f"""These are translations of the same passage:

{texts_formatted}

Source: {pair['title']}

Write 2-4 sentences about what the translations reveal. What does each language HAVE to say 
that the others don't? What choices did the translators make, and what do those choices 
encode about how each language (or translator) sees the world?

Focus on specific linguistic phenomena: word order, tense/aspect, articles, 
formality registers, untranslatable words, or where translators diverged and why.

Use HTML tags (<em>, <strong>) not markdown. Keep it under 100 words."""

    system = "You are a translation theorist who sees the gap between languages as the most interesting place in the world. You notice what each language is forced to commit to that others can leave ambiguous."

    commentary = ask_claude(prompt, system=system, max_tokens=350, temperature=0.8)

    write_feed(name, {
        "type": "the_diff",
        "timestamp": f"{today()}T09:00:00",
        "title": pair['title'],
        "texts": pair['texts'],
        "commentary": commentary,
    })

if __name__ == '__main__':
    generate()
