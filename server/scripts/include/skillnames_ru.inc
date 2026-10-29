// Русские названия навыков для отображения в сообщениях.
// Ключи — внутренние имена навыков POL (uoskills/attribute).

function SkillNameRu(name)
  var map := dictionary;
  map["Alchemy"] := "Алхимия";
  map["Anatomy"] := "Анатомия";
  map["AnimalLore"] := "Знание животных";
  map["Animal Lore"] := "Знание животных";
  map["ItemID"] := "Опознание предметов";
  map["Item Identification"] := "Опознание предметов";
  map["ArmsLore"] := "Знание оружия";
  map["Arms Lore"] := "Знание оружия";
  map["Parry"] := "Парирование";
  map["Begging"] := "Попрошайничество";
  map["Blacksmithy"] := "Кузнечное дело";
  map["Bowcraft"] := "Изготовление луков";
  map["Peacemaking"] := "Умиротворение";
  map["Camping"] := "Выживание";
  map["Carpentry"] := "Плотницкое дело";
  map["Cartography"] := "Картография";
  map["Cooking"] := "Кулинария";
  map["DetectingHidden"] := "Обнаружение скрытого";
  map["DetectHidden"] := "Обнаружение скрытого";
  map["Enticement"] := "Соблазн";
  map["EvaluatingIntelligence"] := "Оценка интеллекта";
  map["EvalInt"] := "Оценка интеллекта";
  map["Healing"] := "Лечение";
  map["Fishing"] := "Рыбалка";
  map["ForensicEvaluation"] := "Судебная экспертиза";
  map["Forensics"] := "Судебная экспертиза";
  map["Herding"] := "Пастушество";
  map["Hiding"] := "Скрытность";
  map["Provocation"] := "Провокация";
  map["Inscription"] := "Надписывание";
  map["Lockpicking"] := "Взлом замков";
  map["Magery"] := "Магия";
  map["MagicResistance"] := "Сопротивление магии";
  map["ResistingSpells"] := "Сопротивление магии";
  map["Tactics"] := "Тактика";
  map["Snooping"] := "Подглядывание";
  map["Musicianship"] := "Музыкальность";
  map["Poisoning"] := "Отравление";
  map["Archery"] := "Стрельба из лука";
  map["SpiritSpeak"] := "Разговор с духами";
  map["Stealing"] := "Кража";
  map["Tailoring"] := "Портняжное дело";
  map["AnimalTaming"] := "Приручение животных";
  map["Taming"] := "Приручение животных";
  map["TasteIdentification"] := "Определение вкуса";
  map["TasteID"] := "Определение вкуса";
  map["Tinkering"] := "Ремесло";
  map["Tracking"] := "Выслеживание";
  map["Veterinary"] := "Ветеринария";
  map["Swordsmanship"] := "Владение мечом";
  map["Macefighting"] := "Владение булавой";
  map["Fencing"] := "Фехтование";
  map["Wrestling"] := "Борьба";
  map["Lumberjacking"] := "Лесозаготовка";
  map["Mining"] := "Горное дело";
  map["Meditation"] := "Медитация";
  map["Stealth"] := "Скрытное передвижение";
  map["RemoveTrap"] := "Обезвреживание ловушек";
  map["Necromancy"] := "Некромантия";
  map["Focus"] := "Сосредоточение";
  map["Chivalry"] := "Рыцарство";
  map["Spellweaving"] := "Плетение заклинаний";
  map["Bushido"] := "Бусидо";
  map["Ninjitsu"] := "Ниндзяцу";
  map["Throwing"] := "Метание";
  map["Mysticism"] := "Мистицизм";
  map["Imbuing"] := "Инкрустация";
  map["Discordance"] := "Дисгармония";
  if (name in map)
    return map[name];
  endif
  return name;
endfunction
