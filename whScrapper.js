var getIds = function() {
	let list = document.getElementsByClassName("listview-cleartext")
	let result = []
	for (var i = 0; i < list.length; i++) {
		let substr = list[i].href.substr(list[i].href.indexOf("=")+1)
		let idstr = substr.substr(0,substr.indexOf('/'))
		 result.push({
		 	"name": list[i].innerHTML,
		 	"entry" : parseInt(idstr)
		 })
	}
	console.log((result))
	console.log(result.map(i=> ""+i.entry))
}
getIds()


var getHighestIlvlId = function () {
    // Get all table rows that actually contain data
    const rows = document.querySelectorAll("tbody.clickable tr.listview-row");

    let best = null;

    rows.forEach(row => {
        // ILvl is the 4th <td> (index 3)
        const cells = row.querySelectorAll("td");

        const ilvl = parseInt(cells[3].textContent.trim(), 10);
        if (isNaN(ilvl)) return;

        // Get the <a> containing the item link (same one you used in your previous script)
        const link = row.querySelector("a.listview-cleartext");
        if (!link) return;

        // Extract item ID from link.href
        const href = link.href;
        const id = parseInt(href.substring(href.indexOf("=") + 1, href.indexOf("/", href.indexOf("="))), 10);

        if (!best || ilvl > best.ilvl) {
            best = { id, ilvl };
        }
    });

    if (best) {
        console.log("Highest ILvl item ID:");
        console.log(best.id)
        console.log("ILvl:" )
        console.log(best.ilvl)
    } else {
        console.log("No items found.");
    }
};

getHighestIlvlId();
