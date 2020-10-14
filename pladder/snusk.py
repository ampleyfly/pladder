from contextlib import ExitStack
import random
import sqlite3


# Words with scores lower than or equal to this will not be included in random picks
SKIP_SCORE = -3


class SnuskDb(ExitStack):
    def __init__(self, db_file_path):
        super().__init__()
        self._db = sqlite3.connect(db_file_path)
        self.callback(self._db.close)
        self._setup()

    def _setup(self):
        with self._db:
            c = self._db.cursor()

            # Nouns
            c.execute("""
                CREATE TABLE IF NOT EXISTS nouns (
                    prefix TEXT,
                    suffix TEXT,
                    score  INTEGER DEFAULT 0,
                    UNIQUE(prefix, suffix)
                );
            """)
            c.execute("PRAGMA table_info(nouns);")
            if len(c.fetchall()) < 3:
                c.execute("ALTER TABLE nouns ADD COLUMN score INTEGER DEFAULT 0;")
            c.execute("SELECT COUNT(*) = 0 FROM nouns;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO nouns (prefix, suffix) VALUES ('frukt', 'frukten');")

            # Inbetweenies
            c.execute("""
                CREATE TABLE IF NOT EXISTS inbetweenies (
                    inbetweeny TEXT UNIQUE,
                    score      INTEGER DEFAULT 0
                );
            """)
            c.execute("PRAGMA table_info(inbetweenies);")
            if len(c.fetchall()) < 2:
                c.execute("ALTER TABLE inbetweenies ADD COLUMN score INTEGER DEFAULT 0;")
            c.execute("SELECT COUNT(*) = 0 FROM inbetweenies;")
            if c.fetchone()[0]:
                c.execute("INSERT INTO inbetweenies (inbetweeny) VALUES ('i');")

    def snusk(self):
        return self._format_parts(self._random_parts())

    def directed_snusk(self, target):
        parts = self._random_parts()
        i = random.choice([0, 1, 3, 4])
        if i in [0, 3]:
            part = target
        else:
            part = target + "ern"
        parts[i] = part
        return self._format_parts(parts)

    def taste(self):
        parts = self._random_parts()
        return "{}/{}".format(parts[0].upper(), parts[3].upper())

    def nick(self):
        parts = self._random_parts()
        return parts[random.choice([0, 1])]

    def example_snusk(self, a, b):
        parts = self._random_parts()
        if random.choice([False, True]):
            parts[0] = a
            parts[4] = b
        else:
            parts[1] = b
            parts[3] = a
        return self._format_parts(parts)

    def example_snusk_with_inbetweeny(self, inbetweeny):
        parts = self._random_parts()
        parts[2] = inbetweeny
        return self._format_parts(parts)

    def _format_parts(self, parts):
        return "{}{} {} {}{}".format(*parts)

    def _random_parts(self):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                WITH
                random_noun AS (
                    SELECT rowid
                    FROM nouns
                    WHERE score > :skip_score
                    ORDER BY RANDOM()
                    LIMIT 1
                ),
                random_inbetweeny AS (
                    SELECT rowid
                    FROM inbetweenies
                    WHERE score > :skip_score
                    ORDER BY RANDOM()
                    LIMIT 1
                )
                SELECT a.prefix, b.suffix, c.inbetweeny, d.prefix, e.suffix
                FROM nouns a, nouns b, inbetweenies c, nouns d, nouns e
                WHERE a.rowid IN random_noun
                AND b.rowid IN random_noun
                AND c.rowid IN random_inbetweeny
                AND d.rowid IN random_noun
                AND e.rowid IN random_noun;
            """, {"skip_score": SKIP_SCORE})
            return list(c.fetchone())

    def add_noun(self, prefix, suffix):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO nouns (prefix, suffix) VALUES (?, ?);", (prefix, suffix))
                return True
            except sqlite3.IntegrityError:
                return False

    def add_inbetweeny(self, inbetweeny):
        with self._db:
            c = self._db.cursor()
            try:
                c.execute("INSERT INTO inbetweenies (inbetweeny) VALUES (?);", (inbetweeny,))
                return True
            except sqlite3.IntegrityError:
                return False

    def find_noun(self, word):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                SELECT prefix, suffix
                FROM nouns
                WHERE ? IN (prefix, suffix);
            """, (word,))
            return c.fetchall()

    def add_noun_score(self, prefix, suffix, delta):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                UPDATE nouns
                SET score = score + ?
                WHERE prefix = ? AND suffix = ?;
            """, (delta, prefix, suffix))
            c.execute("""
                SELECT score
                FROM nouns
                WHERE prefix = ? AND suffix = ?;
            """, (prefix, suffix))
            row = c.fetchone()
            return None if row is None else row[0]

    def add_inbetweeny_score(self, inbetweeny, delta):
        with self._db:
            c = self._db.cursor()
            c.execute("""
                UPDATE inbetweenies
                SET score = score + ?
                WHERE inbetweeny = ?;
            """, (delta, inbetweeny))
            c.execute("""
                SELECT score
                FROM inbetweenies
                WHERE inbetweeny = ?;
            """, (inbetweeny,))
            row = c.fetchone()
            return None if row is None else row[0]


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("db_file_path")
    parser.add_argument("--import-noun-json")
    parser.add_argument("--import-inbetweeny-json")
    args = parser.parse_args()

    with SnuskDb(args.db_file_path) as db:
        if args.import_noun_json:
            with open(args.import_noun_json, "rt") as f:
                nouns = json.load(f)
            for prefix, suffix in nouns:
                db.add_noun(prefix, suffix)
        if args.import_inbetweeny_json:
            with open(args.import_inbetweeny_json, "rt") as f:
                inbetweenies = json.load(f)
            for inbetweeny in inbetweenies:
                db.add_inbetweeny(inbetweeny)
        print(db.snusk())
        print(db.directed_snusk("raek"))
        print(db.example_snusk("don", "donet"))
