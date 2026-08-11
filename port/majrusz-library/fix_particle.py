import re

with open('common/src/main/java/com/majruszlibrary/client/CustomParticle.java', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern: consumer.addVertex( avector3f[ N ] )\n\t\t\t.setUv( fX, fY )\n\t\t\t.setColor( this.rCol, this.gCol, this.bCol, this.alpha )\n\t\t\t.setLight( light )
# Replace with: consumer.setUv( fX, fY ).setColor( this.rCol, this.gCol, this.bCol, this.alpha ).setLight( light ).addVertex( avector3f[ N ] );

pattern = r'consumer\.addVertex\( (avector3f\[\s*\d+\s*\]) \)\s*\.setUv\( ([^)]+) \)\s*\.setColor\( ([^)]+) \)\s*\.setLight\( ([^)]+) \)'
replacement = r'consumer.setUv( \2 ).setColor( \3 ).setLight( \4 ).addVertex( \1 )'

content = re.sub(pattern, replacement, content)

with open('common/src/main/java/com/majruszlibrary/client/CustomParticle.java', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
